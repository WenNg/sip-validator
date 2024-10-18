import os
import csv
import re
from collections import OrderedDict

def validate_special_characters(string):
    # Accept only alphanumeric characters and ( ) _ - for identifier validation
    return bool(re.match(r'^[a-zA-Z0-9\(\)_-]+$', string))

def check_directory_structure(root_path):
    # Add "Supporting Information" and "readme" to the required folders
    required_folders = ['Data', 'Manifest', 'Metadata', 'Supporting Information', 'readme']
    errors = OrderedDict()
    
    try:
        existing_folders = os.listdir(root_path)
    except Exception as e:
        errors[f"Error accessing directory {root_path}: {str(e)}"] = None
        return errors
    
    # Check for required folders without checking capitalization
    extra_folders = [folder for folder in existing_folders if folder.lower() not in [f.lower() for f in required_folders] and os.path.isdir(os.path.join(root_path, folder))]
    for folder in required_folders:
        if not any(f.lower() == folder.lower() for f in existing_folders):
            errors[f"Missing required folder: {folder}"] = None
    
    # Check for README.md or README.txt in the root directory or 'readme' folder
    readme_exists = False
    for fname in os.listdir(root_path):
        if fname.lower() in ['readme.md', 'readme.txt']:
            readme_exists = True
            break
    
    # Also check in a 'readme' folder, if it exists
    readme_folder = os.path.join(root_path, 'readme')
    if os.path.exists(readme_folder) and os.path.isdir(readme_folder):
        for fname in os.listdir(readme_folder):
            if fname.lower() in ['readme.md', 'readme.txt']:
                readme_exists = True
                break

    if not readme_exists:
        errors["Missing README file with .txt or .md extension"] = None
    
    if extra_folders:
        errors[f"Extra folders found: {', '.join(extra_folders)}"] = None
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
    required_fields = ['identifier', 'title', 'visibility']
    
    if not os.path.exists(metadata_path):
        receipt["Missing required folder: Metadata"] = None
        return receipt
    
    # Ensure either 'rights' or 'license' is present
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

            # Validate rights and license fields
            for row in rows:
                identifier = row.get('identifier', 'unknown').strip()
                
                # Validate identifier
                if not validate_special_characters(identifier):
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Invalid identifier."] = None
                
                # Validate rights or license
                if 'rights' in row and not re.match(r'https?://rightsstatements.org/vocab/(InC|InC-OW-EU|InC-EDU|InC-NC|InC-RUU|NoC-CR|NoC-NC|NoC-OKLR|NoC-US|CNE|UND|NKC)/1.0/', row['rights'], re.IGNORECASE):
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Invalid value for rights: {row['rights']}"] = None
                elif 'license' in row and not re.match(r'https?://creativecommons.org/licenses/(by/2.0|by/4.0|by-sa/4.0|by-nd/4.0|by-nc/4.0|by-nc-sa/4.0|by-nc-nd/4.0)/', row['license'], re.IGNORECASE):
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Invalid value for license: {row['license']}"] = None
                elif 'rights' not in row and 'license' not in row:
                    receipt[f"Validation error in {file_name} (identifier {identifier}): Missing required field: either 'rights' or 'license'"] = None

    return receipt  # Always return the receipt, even if empty

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
