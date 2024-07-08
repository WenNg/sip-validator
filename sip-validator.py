import os
import csv
import re
from datetime import datetime
from urllib.parse import urlparse
import time
from PIL import Image

class SIPValidator:
    def __init__(self):
        self.errors = []
        self.non_unique_rows = []

        ## make dynamic for these variables
        self.required_collection_fields = ['identifier', 'title', 'description', 'visibility', 'rights_holder', 'rights']
        self.required_item_fields = ['identifier', 'title', 'description', 'display_date', 'start_date', 'end_date',
                                     'rights_holder', 'rights', 'tags','type', 'language','visibility']

    def has_special_characters(self, text):
        special_characters = r'[@#$%&*/!]'

        if text is None:
            return False

        parsed_url = urlparse(text)
        if parsed_url.scheme and parsed_url.netloc:
            return False

        return bool(re.search(special_characters, text))

    def check_naming_convention(self, name, folder):
        if self.has_special_characters(name):
            self.errors.append(f"Error: Special characters found in '{name}' of folder '{folder}'")

    def check_special_characters_in_fields(self, row, row_number, identifier, file_name, fields):
        field_errors = []
        for field in fields:
            value = row.get(field)
            if self.has_special_characters(value):
                field_errors.append(f"Error: Special characters found in '{file_name}', Row {row_number}, Identifier {identifier}, Field '{field}'")
        return field_errors

    def validate_date_format(self, date_string, row_number, identifier, file_name):
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
        except ValueError:
            self.errors.append(f"Error: Incorrect date format in '{file_name}', Row {row_number}")

    def validate_csv_file(self, file_path, required_fields):
        try:
            with open(file_path, 'r', encoding='utf-8-sig', newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                fields = reader.fieldnames

                if sorted(required_fields) != sorted(fields):
                    incorrect_missing_fields = [field for field in fields if field not in required_fields]

                for field in required_fields:
                    if field not in fields:
                        self.errors.append(f"Error: Missing required field '{field}' in '{os.path.basename(file_path)}'")

                identifiers = set()
                for row_number, row in enumerate(reader, start=2): 
                    identifier = row.get('identifier')
                    if identifier in identifiers:
                        self.non_unique_rows.append(row)
                    else:
                        identifiers.add(identifier)

                    start_date = row.get('start_date')
                    if start_date:
                        self.validate_date_format(start_date, row_number, identifier, os.path.basename(file_path))

                    field_errors = self.check_special_characters_in_fields(row, row_number, identifier, os.path.basename(file_path), fields)
                self.errors.extend(field_errors)
        except Exception as e:
            self.errors.append(f"Error reading CSV file '{os.path.basename(file_path)}': {str(e)}")

        return self.errors, self.non_unique_rows

    def validate_folder_structure(self, sip_root_path, expected_structure):
        for folder, items in expected_structure.items():
            folder_path = os.path.join(sip_root_path, folder)
            self.check_naming_convention(folder, "")

            if not os.path.exists(folder_path):
                self.errors.append(f"Error: Missing folder '{folder}'")

            for item in items:
                if item.lower().endswith('.csv'):
                    item_regex = re.compile(r".*?" + re.escape(item) + r"$", re.IGNORECASE)
                    csv_files = [file for file in os.listdir(folder_path) if item_regex.match(file)]
                    for csv_file in csv_files:
                        item_path = os.path.join(folder_path, csv_file)
                        self.validate_csv_file(item_path, self.required_collection_fields if csv_file.lower() == 'collection_metadata.csv' else self.required_item_fields)
                else:
                    item_path = os.path.join(folder_path, item)
                    self.check_naming_convention(item, folder)

                    if not os.path.exists(item_path):
                        self.errors.append(f"Error: Missing item '{item}' in folder '{folder}'")

        return self.errors

    def validate_metadata_files(self, metadata_folder):
        collection_metadata_files = [file for file in os.listdir(metadata_folder) if file.lower().endswith('_collection_metadata.csv')]
        if not collection_metadata_files:
            self.errors.append(f"Error: Missing collection metadata file with the expected naming convention in the Metadata folder")
        else:
            for collection_metadata_file in collection_metadata_files:
                self.validate_csv_file(os.path.join(metadata_folder, collection_metadata_file), self.required_collection_fields)

        item_metadata_files = [file for file in os.listdir(metadata_folder) if file.lower().endswith('_item_metadata.csv')]
        if not item_metadata_files:
            self.errors.append(f"Error: Missing item metadata file with the expected naming convention in the Metadata folder")
        else:
            for item_metadata_file in item_metadata_files:
                self.validate_csv_file(os.path.join(metadata_folder, item_metadata_file), self.required_item_fields)

        return self.errors

    def validate_digital_objects(self, digital_objects_folder, current_metadata_level):

        #make dynamic
        acceptable_formats = ['TIFF', 'PDF', 'JPG', 'JPEG', 'PNG', 'GIF', 'WAVE', 'WAV', 'MP3', 'MOV', 'MKV', 'MP4',
                              'AVI', 'CSV', 'XML', 'XLSX', 'TXT', 'HTML', 'SGML', 'RTF', 'X3D', 'GLB', 'STL', 'CGM',
                              'PDF/A', 'TIFF', 'SHP', 'SVG','PPTX', 'MBOX' , 'TIF']

        file_formats = set()
        for root, _, files in os.walk(digital_objects_folder):
            for file in files:
                _, file_extension = os.path.splitext(file)
                file_format = file_extension.upper()[1:]
                file_formats.add(file_format)

        if not file_formats:
            self.errors.append(f"Images in Data folder do not have the acceptable file formats.")

        return self.errors

    def validate_special_characters_in_files(self, sip_root_path):
        for root, dirs, files in os.walk(sip_root_path):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                self.check_naming_convention(dir, os.path.relpath(dir_path, sip_root_path))

            for file in files:
                file_path = os.path.join(root, file)
                if self.has_special_characters(file):
                    self.errors.append(f"Error: Special characters found in file name '{file_path}'")

    def validate_sip_structure(self, sip_root_path, expected_structure):
        current_metadata_level = None
        collection_metadata_name = None
        existing_collection_metadata = False  # Flag to track if collection_metadata.csv existed before
        for error in self.errors:
            if "Bronze" in error:
                current_metadata_level = "Bronze"
            elif "Silver" in error:
                current_metadata_level = "Silver"
            elif "Gold" in error:
                current_metadata_level = "Gold"

        folder_structure_errors = self.validate_folder_structure(sip_root_path, expected_structure)
        self.errors.extend(folder_structure_errors)

        metadata_folder = os.path.join(sip_root_path, 'Metadata')
        metadata_errors = self.validate_metadata_files(metadata_folder)
        self.errors.extend(metadata_errors)

        digital_objects_folder = os.path.join(sip_root_path, 'Data')
        digital_objects_errors = self.validate_digital_objects(digital_objects_folder, current_metadata_level)
        self.errors.extend(digital_objects_errors)

        self.validate_special_characters_in_files(sip_root_path)

        if 'collection_metadata.csv' in expected_structure.get('Metadata', []):
            collection_metadata_name = 'collection_metadata.csv'
            metadata_files = [file.lower() for file in os.listdir(metadata_folder)]
            if any(file.endswith('collection_metadata.csv') for file in metadata_files):
                existing_collection_metadata = True  # Marking existing collection_metadata.csv
            else:
                supporting_info_folder = os.path.join(sip_root_path, 'Supporting Information')
                if not os.path.exists(supporting_info_folder):
                    self.errors.append("Error: Missing Supporting Information folder")

                associated_image_found = False
                for file in os.listdir(supporting_info_folder):
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff')):
                        associated_image_found = True
                        break

                if not associated_image_found:
                    self.errors.append(f"Error: No associated image found in Supporting Information folder for the '{collection_metadata_name}'")

        return self.errors, collection_metadata_name, existing_collection_metadata

    def generate_receipt(self, sip_root_path, collection_metadata_name, existing_collection_metadata):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        receipt_path = os.path.join(sip_root_path, f'validation_receipt_{timestamp}.txt')

        for file in os.listdir(sip_root_path):
            if file.startswith('validation_receipt_') and file.endswith('.txt'):
                os.remove(os.path.join(sip_root_path, file))

        with open(receipt_path, 'w', encoding='utf-8') as receipt_file:
            error_set = set(self.errors)
            self.errors = list(error_set)
            for error in self.errors:
                receipt_file.write(f"{error}\n")

            if collection_metadata_name and existing_collection_metadata:
                receipt_file.write(f"collection_metadata.csv existed before.\n")

            receipt_file.write("\nValidation completed successfully.")

        return receipt_path

# # Example usage
# if __name__ == "__main__":
#     validator = SIPValidator()
#     sip_root_path = 'path_to_sip_root_directory'
#     expected_structure = {
#         'Metadata': ['collection_metadata.csv', 'item_metadata.csv'],
#         'Data': ['data_item_1.jpg', 'data_item_2.pdf'],
#         'Supporting Information': ['supporting_doc_1.pdf']
#     }

#     errors, collection_metadata_name, existing_collection_metadata = validator.validate_sip_structure(sip_root_path, expected_structure)
#     if errors:
#         print("Errors found during validation:")
#         for error in errors:
#             print(error)
#     else:
#         print("No errors found.")

#     receipt_path = validator.generate_receipt(sip_root_path, collection_metadata_name, existing_collection_metadata)
#     print(f"Validation receipt generated at: {receipt_path}")
