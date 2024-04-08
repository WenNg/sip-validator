import os
import csv
import re
from datetime import datetime
from urllib.parse import urlparse
import time
from PIL import Image

errors = []
non_unique_rows = []
required_collection_fields = ['identifier', 'title', 'description', 'visibility', 'rights_holder', 'rights']
required_item_fields = ['identifier', 'title', 'description', 'display_date', 'start_date', 'end_date',
                        'rights_holder', 'rights_statement', 'tags', 'parent_collection', 'type',
                        'language', 'extent', 'visibility']

def has_special_characters(text):
    special_characters = r'[@#$%&*/!]'

    if text is None:
        return False

    parsed_url = urlparse(text)
    if parsed_url.scheme and parsed_url.netloc:
        return False

    return bool(re.search(special_characters, text))

def check_naming_convention(name, folder):
    if has_special_characters(name):
        errors.append(f"Error: Special characters found in '{name}' of folder '{folder}'")

def check_special_characters_in_fields(row, row_number, identifier, file_name, fields):
    field_errors = []
    for field in fields:
        value = row.get(field)
        if has_special_characters(value):
            field_errors.append(f"Error: Special characters found in '{file_name}', Row {row_number}, Identifier {identifier}, Field '{field}'")

    return field_errors

def validate_date_format(date_string, row_number, identifier, file_name):
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        errors.append(f"Error: Incorrect date format in '{file_name}', Row {row_number}")

def validate_csv_file(file_path, required_fields):
    try:
       with open(file_path, 'r', encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            fields = reader.fieldnames

            if sorted(required_fields) != sorted(fields):
                incorrect_missing_fields = [field for field in fields if field not in required_fields]

            for field in required_fields:
                if field not in fields:
                    errors.append(f"Error: Missing required field '{field}' in '{os.path.basename(file_path)}'")

            identifiers = set()
            for row_number, row in enumerate(reader, start=2): 
                identifier = row.get('identifier')
                if identifier in identifiers:
                    non_unique_rows.append(row)
                else:
                    identifiers.add(identifier)

                start_date = row.get('start_date')
                if start_date:
                    validate_date_format(start_date, row_number, identifier, os.path.basename(file_path))

                field_errors = check_special_characters_in_fields(row, row_number, identifier, os.path.basename(file_path), fields)
            errors.extend(field_errors)
    except Exception as e:
        errors.append(f"Error reading CSV file '{os.path.basename(file_path)}': {str(e)}")

    return errors, non_unique_rows

def validate_folder_structure(sip_root_path, expected_structure):
    for folder, items in expected_structure.items():
        folder_path = os.path.join(sip_root_path, folder)
        check_naming_convention(folder, "")

        if not os.path.exists(folder_path):
            errors.append(f"Error: Missing folder '{folder}'")

        for item in items:
            if item.lower().endswith('.csv'):
                item_regex = re.compile(r".*?" + re.escape(item) + r"$", re.IGNORECASE)
                csv_files = [file for file in os.listdir(folder_path) if item_regex.match(file)]
                for csv_file in csv_files:
                    item_path = os.path.join(folder_path, csv_file)
                    validate_csv_file(item_path, required_collection_fields if csv_file.lower() == 'collection_metadata.csv' else required_item_fields)
            else:
                item_path = os.path.join(folder_path, item)
                check_naming_convention(item, folder)

                if not os.path.exists(item_path):
                    errors.append(f"Error: Missing item '{item}' in folder '{folder}'")

    return errors

def validate_metadata_files(metadata_folder, required_collection_fields, required_item_fields):
    collection_metadata_files = [file for file in os.listdir(metadata_folder) if file.lower().endswith('_collection_metadata.csv')]
    if not collection_metadata_files:
        errors.append(f"Error: Missing collection metadata file with the expected naming convention in the Metadata folder")
    else:
        for collection_metadata_file in collection_metadata_files:
            validate_csv_file(os.path.join(metadata_folder, collection_metadata_file), required_collection_fields)

    item_metadata_files = [file for file in os.listdir(metadata_folder) if file.lower().endswith('_item_metadata.csv')]
    if not item_metadata_files:
        errors.append(f"Error: Missing item metadata file with the expected naming convention in the Metadata folder")
    else:
        for item_metadata_file in item_metadata_files:
            validate_csv_file(os.path.join(metadata_folder, item_metadata_file), required_item_fields)

    return errors


def validate_digital_objects(digital_objects_folder, current_metadata_level):

    acceptable_formats = ['TIFF', 'PDF', 'JPG', 'JPEG', 'PNG', 'GIF', 'WAVE', 'WAV', 'MP3', 'MOV', 'MKV', 'MP4',
                          'AVI', 'CSV', 'XML', 'XLSX', 'TXT', 'HTML', 'SGML', 'RTF', 'X3D', 'GLB', 'STL', 'CGM',
                          'PDF/A', 'TIFF', 'SHP', 'SVG','PPTX', 'MBOX' , 'TIF']

    # dpi_levels = {'Bronze': 300, 'Silver': 400, 'Gold': (400, 600)}
    file_formats = set()
    # low_dpi_count = 0
    for root, _, files in os.walk(digital_objects_folder):
        for file in files:
            _, file_extension = os.path.splitext(file)
            file_format = file_extension.upper()[1:]
            file_formats.add(file_format)

            if file_format.upper() in acceptable_formats:
                image_path = os.path.join(root, file)
    #             dpi = calculate_dpi(image_path)
    #             if current_metadata_level and dpi < dpi_levels[current_metadata_level]:
    #                 low_dpi_count += 1
    # validation_level = None
    # if file_formats.issuperset(acceptable_formats) and low_dpi_count == 0:
    #     validation_level = 'Gold'
    # elif file_formats.issuperset(acceptable_formats) and low_dpi_count <= len(files) * 0.1:
    #     validation_level = 'Silver'
    # elif file_formats.issuperset(acceptable_formats) and low_dpi_count > len(files) * 0.1:
    #     validation_level = 'Bronze'

    # if validation_level:
    if not file_formats:
        # errors.append(f"{validation_level}: Acceptable file formats, images have DPI lower than {current_metadata_level} level ({dpi_levels[current_metadata_level]})")
        # errors.append(f"Acceptable file formats.")
    # else:
        # errors.append(f"Images in Data folder do not meet the minimum level DPI requirements.")
        errors.append(f"Images in Data folder do not have the acceptable file formats.")

    return errors


# def calculate_dpi(image_path):
#     try:
#         image = Image.open(image_path)
#         width, height = image.size
#         dpi_x, dpi_y = image.info.get('dpi', (0, 0))
#         if dpi_x == 0 or dpi_y == 0:
#             # If 'dpi' key is not found or has a zero value, calculate DPI using physical dimensions
#             physical_width = width / 25.4  # Convert width to inches
#             physical_height = height / 25.4  # Convert height to inches
#             dpi_x = int(width / physical_width)
#             dpi_y = int(height / physical_height) 
#         return dpi_x
#     except Exception as e:
#         print(f"Error: {e}")
#         return 0


def validate_special_characters_in_files(sip_root_path):
    for root, dirs, files in os.walk(sip_root_path):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            check_naming_convention(dir, os.path.relpath(dir_path, sip_root_path))

        for file in files:
            file_path = os.path.join(root, file)

            if has_special_characters(file):
                errors.append(f"Error: Special characters found in file name '{file_path}'")

def validate_sip_structure(sip_root_path, expected_structure, required_collection_fields, required_item_fields):
    current_metadata_level = None
    collection_metadata_name = None
    existing_collection_metadata = False  # Flag to track if collection_metadata.csv existed before
    for error in errors:
        if "Bronze" in error:
            current_metadata_level = "Bronze"
        elif "Silver" in error:
            current_metadata_level = "Silver"
        elif "Gold" in error:
            current_metadata_level = "Gold"

    folder_structure_errors = validate_folder_structure(sip_root_path, expected_structure)
    errors.extend(folder_structure_errors)

    metadata_folder = os.path.join(sip_root_path, 'Metadata')
    metadata_errors = validate_metadata_files(metadata_folder, required_collection_fields, required_item_fields)
    errors.extend(metadata_errors)

    digital_objects_folder = os.path.join(sip_root_path, 'Data')
    digital_objects_errors = validate_digital_objects(digital_objects_folder, current_metadata_level)
    errors.extend(digital_objects_errors)

    validate_special_characters_in_files(sip_root_path)

    if 'collection_metadata.csv' in expected_structure.get('Metadata', []):
        collection_metadata_name = 'collection_metadata.csv'
        metadata_files = [file.lower() for file in os.listdir(metadata_folder)]
        if any(file.endswith('collection_metadata.csv') for file in metadata_files):
            existing_collection_metadata = True  # Marking existing collection_metadata.csv
        else:
            supporting_info_folder = os.path.join(sip_root_path, 'Supporting Information')
            if not os.path.exists(supporting_info_folder):
                errors.append("Error: Missing Supporting Information folder")

            associated_image_found = False
            for file in os.listdir(supporting_info_folder):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff')):
                    associated_image_found = True
                    break

            if not associated_image_found:
                errors.append(f"Error: No associated image found in Supporting Information folder for the '{collection_metadata_name}'")

    return errors, collection_metadata_name, existing_collection_metadata


def generate_receipt(errors, non_unique_rows, sip_root_path, collection_metadata_name, existing_collection_metadata):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    receipt_path = os.path.join(sip_root_path, f'validation_receipt_{timestamp}.txt')

    for file in os.listdir(sip_root_path):
        if file.startswith('validation_receipt_') and file.endswith('.txt'):
            os.remove(os.path.join(sip_root_path, file))

    with open(receipt_path, 'w', encoding='utf-8') as receipt_file:
        error_set = set(errors)
        errors = list(error_set)
        if not errors and not non_unique_rows:
            receipt_file.write("Validation successful. The SIP structure is correct.\n")
        elif non_unique_rows:
            receipt_file.write("Validation successful, but with non-unique identifiers. Non-unique rows:\n")
            for row in non_unique_rows:
                receipt_file.write(f"{row}\n")
        else:
            receipt_file.write("Validation Errors:\n")
            for i, error in enumerate(errors, 1):
                receipt_file.write(f"{error}\n")
                if i % 4 == 0:
                    receipt_file.write("\n")
            receipt_file.write("Please fix above errors before proceeding further.")        
            

        # Add additional comment when 'collection_metadata.csv' is missing
        if not any(file.lower().endswith('collection_metadata.csv') for file in os.listdir(os.path.join(sip_root_path, 'Metadata'))):
            receipt_file.write("\nIf adding a new collection, make sure you have both item_metadata.csv and collection_metadata.csv files.\n"
                               "If you are adding items to an existing collection, you would only need item_metadata.csv. \n"
                               "Please ignore the validation failed message.")

    validation_levels = set()
    metadata_fields = {
        "Bronze": ['identifier', 'title', 'rights'],
        "Silver": ['identifier', 'title', 'rights', 'subject', 'medium', 'type', 'start_date', 'tags'],
        "Gold": ['identifier', 'title', 'rights', 'subject', 'medium', 'type', 'start_date', 'tags', 'location']
    }

    # dpi_levels = {'Bronze': 300, 'Silver': 400, 'Gold': (400, 600)}

    for error in errors:
        if "Bronze" in error:
            validation_levels.add("Bronze")
        elif "Silver" in error:
            validation_levels.add("Silver")
        elif "Gold" in error:
            validation_levels.add("Gold")

    if 'Gold' in validation_levels:
        current_level = "Gold"
    elif 'Silver' in validation_levels:
        current_level = "Silver"
    elif 'Bronze' in validation_levels:
        current_level = "Bronze"
    else:
        current_level = "Validation failed"
    # if current_level == "Validation failed" and receipt_file:
    #     receipt_content = f"\n Validation failed. Please fix above errors before continuing."    
    # else:
    #     receipt_content = f"\nValidation level: {current_level}"

    # if current_level == "Validation failed":
    #     receipt_content += "\nTo reach Bronze level, ensure the SIP structure is correct and all required metadata fields are present.\nEnsure below requirements are met. \n"
    #     # receipt_content += f"Bronze [Mandatory]: Acceptable file formats, images are less than {dpi_levels['Bronze']} DPI"
    #     receipt_content += f"Bronze [Mandatory]: Acceptable file formats."
    #     receipt_content += "\nRequired Metadata:"
    #     for field in metadata_fields["Bronze"]:
    #         receipt_content += f"\n● {field.capitalize()}"
    # elif current_level == "Bronze":
    #     receipt_content += "\nTo reach Silver level, ensure below requirements are met. \n"
    #     # receipt_content += f"Silver: Acceptable or Preferred formats that are open, non-proprietary; DPI {dpi_levels['Silver']}"
    #     receipt_content += f"Bronze [Mandatory]: Acceptable file formats."
    #     receipt_content += "\nAdvanced Metadata:"
    #     for field in metadata_fields["Silver"]:
    #         receipt_content += f"\n● {field.capitalize()}"
    # elif current_level == "Silver":
    #     receipt_content += "\nTo reach Gold level, ensure below requirements are met. \n"
    #     # receipt_content += f"Gold: Preferred format that are open, non-proprietary; DPI between {dpi_levels['Gold'][0]} and {dpi_levels['Gold'][1]}"
    #     receipt_content += f"Bronze [Mandatory]: Acceptable file formats."
    #     receipt_content += "\nGold Standard Metadata includes all Advanced Metadata and any other relevant metadata that you can provide."
    #     receipt_content += "\nAdvanced Metadata:"
    #     for field in metadata_fields["Silver"]:
    #         receipt_content += f"\n● {field.capitalize()}"

    # if existing_collection_metadata:
    #     receipt_content += "\nNo need to check for associated image as collection_metadata.csv already existed."

    # with open(receipt_path, 'a', encoding='utf-8') as receipt_file:
    #     receipt_file.write(receipt_content)

    print(f"Validation completed. Receipt saved to: {receipt_path}")

def main():
    print("Program is running...")

    expected_structure = {
        'Data': [],
        'Metadata': ['collection_metadata.csv', 'item_metadata.csv'],
        'Supporting Information': ['Deposit Agreement', 'Memorandum of Agreement'],
        'Manifest': [],
        'Readme': []
    }

    sip_root_path = input("Enter the path to your SIP root folder: ")

    validation_errors, collection_metadata_name, existing_collection_metadata = validate_sip_structure(sip_root_path, expected_structure, required_collection_fields, required_item_fields)

    generate_receipt(validation_errors, non_unique_rows, sip_root_path, collection_metadata_name, existing_collection_metadata)

    print("Processing completed.")

    print("Closing in 10 seconds...")
    time.sleep(10)

if __name__ == "__main__":
    main()

