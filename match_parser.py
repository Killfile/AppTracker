import json
import os

def fix_json_errors_in_file(file_path):
    """
    Reads a file consisting of JSON objects and converts it to a JSON array of objects by starting and ending the file with brackets and adding a comma following every } character.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix the JSON format
    content = '[' + content.replace('}', '},') + ']'
    content = content.replace(',]', ']')  # Remove trailing comma

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    input_path = os.path.join(os.path.dirname(__file__), 'GmailIngestionWorker/company_name_exhaust.json')
    output_path = os.path.join(os.path.dirname(__file__), 'processed_company_name_exhaust.json')

    # Fix the JSON errors in the input file
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if not os.path.isfile(input_path):
        raise ValueError(f"Input path is not a file: {input_path}")
    # try to open the file and load it as JSON
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}; attempting to fix...")
        fix_json_errors_in_file(input_path)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    filtered = [item for item in data if item.get('match_type') != 'known_email']
    # Group by match_detail
    grouped = {}
    for item in filtered:
        detail = item.get('match_detail')
        # Convert list to string for grouping
        key = str(detail)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)
    # Sort keys alphabetically
    sorted_grouped = {k: grouped[k] for k in sorted(grouped.keys())}

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_grouped, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
