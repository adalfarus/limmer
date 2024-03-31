import re

def parse_message_with_brackets(message):
    # Define a regular expression pattern to match text inside and outside brackets
    pattern = r'(\[[^\]]+\])|([^\[\]]+)'

    # Find all matches of the pattern in the message
    matches = re.findall(pattern, message)

    # Flatten the tuple results and filter out empty matches
    parsed_parts = [part for match in matches for part in match if part]

    return parsed_parts

# Example usage
message = "Text before [BRACKET1] text in between [BRACKET2] and after"
parsed_parts = parse_message_with_brackets(message)

for i, part in enumerate(parsed_parts):
    print(f"Part {i+1}: {part}")
