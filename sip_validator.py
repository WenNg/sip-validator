import os
import csv
import re
import json
from datetime import datetime
from collections import OrderedDict

class SIPValidator:
    def __init__(self, root_path, config):
        self.root_path = root_path
        self.errors = OrderedDict()
        self.config = config['sip_validator']

    @staticmethod
    def validate_date_format(date_text):
        try:
            datetime.strptime(date_text, '%Y/%m/%d')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_special_characters(string):
        return bool(re.match(r'^[a-zA-Z0-9@#$%&*/!\']+$', string.lower()))

    def check_directory_structure(self):
        required_folders = self.config['required_folders']
        try:
            existing_folders = os.listdir(self.root_path)
        except Exception as e:
            self.errors[f"Error accessing directory {self.root_path}: {str(e)}"] = None
            return
        
        extra_folders = [folder for folder in existing_folders if folder not in required_folders and os.path.isdir(os.path.join(self.root_path, folder))]
        for folder in required_folders:
            matched_folders = [f for f in existing_folders if re.match(rf'{folder}[^a-zA-Z0-9]*$', f, re.IGNORECASE)]
            if not matched_folders:
                self.errors[f"Missing required folder: {folder}"] = None
            else:
                for matched_folder in matched_folders:
                    if matched_folder != folder:
                        self.errors[f"Folder name should be {folder} but found {matched_folder}"] = None
                    elif not self.validate_special_characters(matched_folder):
                        self.errors[f"Folder name contains special characters: {matched_folder}"] = None
        if extra_folders:
            self.errors[f"Extra folders found: {', '.join(extra_folders)}"] = None
        if not any(fname.startswith('README') and fname.split('.')[-1] in self.config['readme_extensions'] for fname in existing_folders):
            self.errors["Missing README file with .txt or .md extension"] = None
        if not self.errors:
            self.errors["Directory structure is valid."] = None

    def check_files(self):
        manifest_path = os.path.join(self.root_path, 'Manifest')
        metadata_path = os.path.join(self.root_path, 'Metadata')
        
        # Checking manifest
        if not os.path.exists(manifest_path):
            self.errors["Missing required folder: Manifest"] = None
        else:
            try:
                manifest_files = os.listdir(manifest_path)
            except Exception as e:
                self.errors[f"Error accessing Manifest folder: {str(e)}"] = None
                return
            if self.config['manifest_required_file'] not in manifest_files:
                self.errors[f"Missing required file: {self.config['manifest_required_file']} in Manifest folder"] = None
            extra_files = [file for file in manifest_files if file != self.config['manifest_required_file']]
            if extra_files:
                self.errors[f"Extra files found in Manifest folder: {', '.join(extra_files)}"] = None
        
        # Checking metadata
        if not os.path.exists(metadata_path):
            self.errors["Missing required folder: Metadata"] = None
        else:
            try:
                metadata_files = os.listdir(metadata_path)
            except Exception as e:
                self.errors[f"Error accessing Metadata folder: {str(e)}"] = None
                return
            pattern_collection = re.compile(r'.*collection_metadata\.csv')
            pattern_item = re.compile(r'.*item_metadata\.csv')
            collection_found = any(pattern_collection.match(file.lower()) for file in metadata_files)
            item_found = any(pattern_item.match(file.lower()) for file in metadata_files)
            
            if not collection_found:
                self.errors[f"Missing required *{self.config['metadata_required_files'][0]} file in Metadata folder"] = None
            if not item_found:
                self.errors[f"Missing required *{self.config['metadata_required_files'][1]} file in Metadata folder"] = None
            required_files = {self.config['metadata_required_files'][0]: collection_found, self.config['metadata_required_files'][1]: item_found}
            for file_type, found in required_files.items():
                if found:
                    extra_files = [file for file in metadata_files if not pattern_collection.match(file.lower()) and not pattern_item.match(file.lower())]
                    if extra_files:
                        self.errors[f"Extra files found in Metadata folder: {', '.join(extra_files)}"] = None

        if not self.errors:
            self.errors["All required files inside the folders are present."] = None

    @staticmethod
    def read_csv_file(file_path):
        try:
            with open(file_path, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader((line.lower() for line in file))
                return list(reader)
        except UnicodeDecodeError:
            try:
                with open(file_path, mode='r', newline='', encoding='latin1') as file:
                    reader = csv.DictReader((line.lower() for line in file))
                    return list(reader)
            except Exception as e:
                return str(e)
        except Exception as e:
            return str(e)

    def validate_metadata_files(self):
        metadata_path = os.path.join(self.root_path, 'Metadata')
        required_fields = self.config['required_metadata_fields']
        
        if not os.path.exists(metadata_path):
            self.errors["Missing required folder: Metadata"] = None
            return
        
        # Scan for all metadata files that match the patterns
        for file_name in os.listdir(metadata_path):
            if re.search(r'(collection_metadata\.csv|item_metadata\.csv)$', file_name.lower()):
                file_path = os.path.join(metadata_path, file_name)
                rows = self.read_csv_file(file_path)
                if isinstance(rows, str):  # An error message was returned
                    self.errors[f"Validation error in {file_name}: {rows}"] = None
                    continue
                if not rows:
                    self.errors[f"Validation error in {file_name}: Could not read file or file is empty"] = None
                    continue

                fieldnames_lower = [field.strip() for field in rows[0].keys()]
                
                # Check field names once
                missing_field = False
                for field in required_fields:
                    matched_fields = [f for f in fieldnames_lower if re.match(rf'{field}[^a-zA-Z0-9]*$', f, re.IGNORECASE)]
                    if not matched_fields:
                        self.errors[f"Validation error in {file_name}: Missing required column {field}"] = None
                        missing_field = True
                    else:
                        for matched_field in matched_fields:
                            if matched_field != field:
                                self.errors[f"Validation error in {file_name}: Field name should be {field} but found {matched_field}"] = None
                                missing_field = True
                            elif field != 'rights_holder' and not self.validate_special_characters(matched_field):
                                self.errors[f"Validation error in {file_name}: Field name contains special characters: {matched_field}"] = None
                                missing_field = True

                # If any required field is missing or incorrect, skip row validation
                if missing_field:
                    continue

                # Check each row for content
                for row in rows:
                    identifier = row.get('identifier', 'unknown').strip()
                    
                    # Validate identifier
                    if not self.validate_special_characters(identifier):
                        self.errors[f"Validation error in {file_name} (identifier {identifier}): Invalid identifier."] = None
                    
                    # Validate date format
                    date = row.get('date', '').strip()
                    if date and not self.validate_date_format(date):
                        self.errors[f"Validation error in {file_name} (identifier {identifier}): Invalid date format."] = None
                    
                    # Required fields check
                    for field in required_fields:
                        if field not in row or not row[field].strip():
                            self.errors[f"Validation error in {file_name} (identifier {identifier}): Missing or invalid {field}."] = None

    def write_validation_receipt(self):
        receipt_path = os.path.join(self.root_path, 'validation_receipt.txt')
        with open(receipt_path, 'w') as file:
            for line in self.errors:
                file.write(line + '\n')
            if any("Missing required folder" in line or "Validation error" in line or "Folder name should be" in line for line in self.errors):
                file.write("Validation failed.\n")

    def run_validation(self):
        self.check_directory_structure()
        self.check_files()
        self.validate_metadata_files()
        return self.errors

# if __name__ == "__main__":
#     root_path = input("Enter the path to the SIP directory: ")
#     environment_config_path = 'config.json'  # Path to your main configuration file

#     with open(environment_config_path, 'r') as env_file:
#         env_config = json.load(env_file)
#         environment = env_config["environment"]

#     config_path = f'config_{environment}.json'  # Select the appropriate environment configuration file

#     validator = SIPValidator(root_path, config_path)
#     validation_errors = validator.run_validation()
#     if validation_errors:
#         for error in validation_errors:
#             print(error)
#         validator.write_validation_receipt()
#         print(f"Validation receipt has been written to {os.path.join(root_path, 'validation_receipt.txt')}")
#     else:
#         print("All checks passed. No issues found.")
