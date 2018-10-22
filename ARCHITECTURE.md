# Design decisions
1. regexes alone were found to be unreliable or even buggy for performing replacements,
particularly where leading whitespace is present. To mitigate this, the tool:
    - tracks start and end of non-whitespace on a given line
    - attempts the regex substitution within only the non-whitespace content
    - finally, substitutes that replacement back into the line, retaining existing whitespace
2. in-line replacement was chosen over parsing/comprehending the file format
 as many parsers lose comments and file structure in doing so, which would be
 unacceptable for this project. It should leave the files exactly as found,
 just with a different version number (or other explicitly designated variable).
