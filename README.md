# sip-validator
The SIP (Submission Information Package) Validator is a Python script designed to validate the structure and content of a SIP directory. A SIP typically consists of digital objects, metadata files, supporting information, a manifest, and a Readme file. The script checks for the presence of expected folders and files, validates CSV files' structure, and ensures data integrity.
## references
- [DLP Metadata Application Profile](https://docs.google.com/document/d/1WZUe6fnmbQNRX5crx3YAcHNb6tyuHvfPyBLWoJbAwhM/edit?usp=sharing)
- Virginia Tech Digital Library Submission Information Package
# Prerequisites
- Python 3.x 
- Standard Python libraries: os, csv, re, datetime
# Usage
1.	Save the script as sip-validator.py.
2.	Run the script in a terminal or command prompt: 
python3 sip-validator.py
3.	Enter the path to the SIP root folder when prompted.
# Functionality
1. Folder and File Existence Check
The script verifies the existence of the following folders and files in the SIP:
- Data: Files
- Manifest: checksumsha1
- Metadata: collection_metadata.csv, item_metadata.csv
- README (optional): readme.txt or readme.md either within this folder or in SIP root folder
- Supporting Information
2. CSV File Validation
The script checks the structure and content of collection_metadata.csv and item_metadata.csv:
- collection_metadata.csv
  - Required Fields: identifier, title, visibility.
  - Unique Identifier Check: Ensures each identifier is unique.
  - Special Character Check: Identifier field allowing only alphanumeric characters, underscores _, and hyphens -.
  - Controlled Value Check: Looks for controlled values in rights or license.
- item_metadata.csv
  - Required Fields: identifier, title, rights or license, visibility.
  - Unique Identifier Check: Ensures each identifier is unique.
  - Special Character Check: Identifier field allowing only alphanumeric characters, underscores _, and hyphens -.
  - Controlled Value Check: Looks for controlled values in rights or license.
3. Validation Results
Validation results are saved in a receipt file (validation_receipt.txt) within the SIP root folder:
- Validation Errors: Details errors encountered during validation.
- Non-Unique Identifiers: Lists rows with non-unique identifiers (if applicable).
- Validation Success: Indicates successful validation if no errors are found.
* Example - 
python3 sip-validator.py
* Enter the path to your SIP root folder: /path/to/sip_root
- Validation completed. Receipt saved to: /path/to/sip_root/validation_receipt.txt
