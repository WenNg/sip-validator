import os
import csv
import re
from datetime import datetime
from collections import OrderedDict

def validate_date_format(date_text):
    try:
        datetime.strptime(date_text, '%Y/%m/%d')
        return True
    except ValueError:
        return False

def validate_special_characters(string):
    return bool(re.match(r'^[a-zA-Z0-9@#$%&*/!\']+$', string.lower()))

def check_directory_structure(root_path):
    required_folders = ['Data', 'Manifest', 'Metadata']
    errors = OrderedDict()
    try:
        existing_folders = os.listdir(root_path)
    except Exception as e:
        errors[f"Error accessing directory {root_path}: {str(e)}"] = None
        return errors
    
    extra_folders = [folder for folder in existing_folders if folder not in required_folders and os.path.isdir(os.path.join(root_path, folder))]
    for folder in required_folders:
        matched_folders = [f for f in existing_folders if re.match(rf'{folder}[^a-zA-Z0-9]*$', f, re.IGNORECASE)]
        if not matched_folders:
            errors[f"Missing required folder: {folder}"] = None
        else:
            for matched_folder in matched_folders:
                if matched_folder != folder:
                    errors[f"Folder name should be {folder} but found {matched_folder}"] = None
                elif not validate_special_characters(matched_folder):
                    errors[f"Folder name contains special characters: {matched_folder}"] = None
    if extra_folders:
        errors[f"Extra folders found: {', '.join(extra_folders)}"] = None
    if not any(fname.startswith('README') and fname.split('.')[-1] in ['txt', 'md'] for fname in existing_folders):
        errors["Missing README file with .txt or .md extension"] = None
    if not errors:
        errors["Directory structure is valid."] = None
    return errors

def check_files(root_path):
    manifest_path = os.path.join(root_path, 'Manifest')
    metadata_path = os.path.join(root_path, 'Metadata')
    
    errors = OrderedDict()
    # Checking manifest
    if not os.path.exists(manifest_path):
        errors["Missing required folder: Manifest"] = None
    else:
        try:
            manifest_files = os.listdir(manifest_path)
        except Exception as e:
            errors[f"Error accessing Manifest folder: {str(e)}"] = None
            return errors
        if 'checksumsha1.csv' not in manifest_files:
            errors["Missing required file: checksumsha1.csv in Manifest folder"] = None
        extra_files = [file for file in manifest_files if file != 'checksumsha1.csv']
        if extra_files:
            errors[f"Extra files found in Manifest folder: {', '.join(extra_files)}"] = None
    
    # Checking metadata
    if not os.path.exists(metadata_path):
        errors["Missing required folder: Metadata"] = None
    else:
        try:
            metadata_files = os.listdir(metadata_path)
        except Exception as e:
            errors[f"Error accessing Metadata folder: {str(e)}"] = None
            return errors
        pattern_collection = re.compile(r'.*collection_metadata\.csv')
        pattern_item = re.compile(r'.*item_metadata\.csv')
        collection_found = any(pattern_collection.match(file.lower()) for file in metadata_files)
        item_found = any(pattern_item.match(file.lower()) for file in metadata_files)
        
        if not collection_found:
            errors["Missing required *collection_metadata.csv file in Metadata folder"] = None
        if not item_found:
            errors["Missing required *item_metadata.csv file in Metadata folder"] = None
        required_files = {'collection_metadata': collection_found, 'item_metadata': item_found}
        for file_type, found in required_files.items():
            if found:
                extra_files = [file for file in metadata_files if not pattern_collection.match(file.lower()) and not pattern_item.match(file.lower())]
                if extra_files:
                    errors[f"Extra files found in Metadata folder: {', '.join(extra_files)}"] = None
    
    if not errors:
        errors["All required files inside the folders are present."] = None
    return errors

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

def validate_metadata_files(root_path):
    metadata_path = os.path.join(root_path, 'Metadata')
    receipt = OrderedDict()
    required_fields = ['identifier', 'title', 'description', 'visibility', 'rights_holder']
    
    if not os.path.exists(metadata_path):
        receipt["Missing required folder: Metadata"] = None
        return receipt
    
    # Scan for all metadata files that match the patterns
    for file_name in os.listdir(metadata_path):
        if re.search(r'(collection_metadata\.csv|item_metadata\.csv)$', file_name.lower()):
            file_path = os.path.join(metadata_path, file_name)
            rows = read_csv_file(file_path)
            if isinstance(rows, str):  # An error message was returned
                receipt[f"Validation error in {file_name}: {rows}"] = None
                continue
            if not rows:
                receipt[f"Validation error in {file_name}: Could not read file or file is empty"] = None
                continue

            fieldnames_lower = [field.strip() for field in rows[0].keys()]
                
            # Check field names once
            missing_field = False
            for field in required_fields:
                matched_fields = [f for f in fieldnames_lower if re.match(rf'{field}[^a-zA-Z0-9]*$', f, re.IGNORECASE)]
                if not matched_fields:
                    receipt[f"Validation error in {file_name}: Missing required column {field}"] = None
                    missing_field = True
                else:
                    for matched_field in matched_fields:
                        if matched_field != field:
                            receipt[f"Validation error in {file_name}: Field name should be {field} but found {matched_field}"] = None
                            missing_field = True
                        elif field != 'rights_holder' and not validate_special_characters(matched_field):
                            receipt[f"Validation error in {file_name}: Field name contains special characters: {matched_field}"] = None
                            missing_field = True

            # If any required field is missing or incorrect, skip row validation
            if missing_field:
                continue

            # Check each row for content
            for row in rows:
                identifier = row.get('identifier', 'unknown').strip()
                
                # Validate identifier
                if not validate_special_characters(identifier):
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Invalid identifier."] = None
                
                # Validate date format
                date = row.get('date', '').strip()
                if date and not validate_date_format(date):
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Invalid date format."] = None
                
                # Required fields check
                for field in required_fields:
                    if field not in row or not row[field].strip():
                        receipt[f"Validation error in {file_name} (identifier {identifier}): Missing or invalid {field}."] = None

    return receipt

def write_validation_receipt(receipt, root_path):
    receipt_path = os.path.join(root_path, 'validation_receipt.txt')
    with open(receipt_path, 'w') as file:
        for line in receipt:
            file.write(line + '\n')
        if any("Missing required folder" in line or "Validation error" in line or "Folder name should be" in line for line in receipt):
            file.write("Validation failed.\n")

def main():
    root_path = input("Enter the path to the SIP directory: ")
    
    issues = OrderedDict()

    # Validate directory structure
    issues.update(check_directory_structure(root_path))
    
    # Check files presence
    issues.update(check_files(root_path))
    
    # Validate metadata
    validation_receipt = validate_metadata_files(root_path)
    issues.update(validation_receipt)

    if issues:
        for issue in issues:
            print(issue)
        write_validation_receipt(issues, root_path)
        print(f"Validation receipt has been written to {os.path.join(root_path, 'validation_receipt.txt')}")
    else:
        print("All checks passed. No issues found.")

if __name__ == "__main__":
    main()
