"""
Code Preprocessor - Step 3: Clean and normalize code
"""
import re
import autopep8

class CodePreprocessor:
    def preprocess(self, code, language):
        """
        Preprocess code by cleaning and normalizing
        Returns: dict with cleaned_code and preprocessing_info
        """
        result = {
            'cleaned_code': code,
            'preprocessing_info': {
                'original_lines': len(code.split('\n')),
                'blank_lines_removed': 0,
                'normalized': False
            }
        }
        
        cleaned = self._handle_encoding(code)
        
        result['preprocessing_info']['blank_lines_removed'] = 0
        
        cleaned = self._normalize_indentation(cleaned)
        
        cleaned = '\n'.join(line.rstrip() for line in cleaned.split('\n'))
        
        result['cleaned_code'] = cleaned
        return result
    
    def _handle_encoding(self, code):
        """Remove BOM and handle common encoding issues"""
        if code.startswith('\ufeff'):
            code = code[1:]
        
        code = code.replace('\r\n', '\n').replace('\r', '\n')
        
        return code
    
    def _remove_excessive_blanks(self, code):
        """Remove excessive blank lines, keep max 1 blank line"""
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', code)
        return cleaned
    
    def _normalize_indentation(self, code):
        """Normalize indentation to consistent spaces"""
        lines = code.split('\n')
        normalized_lines = []
        
        indent_style = self._detect_indent_style(code)
        
        for line in lines:
            if line.strip():  
                if '\t' in line:
                    leading_whitespace = len(line) - len(line.lstrip())

                    tabs_count = line[:leading_whitespace].count('\t')
                    spaces_count = line[:leading_whitespace].count(' ')
                    
                    new_indent = ' ' * (tabs_count * 4 + spaces_count)
                    normalized_lines.append(new_indent + line.lstrip())
                else:
                    normalized_lines.append(line)
            else:
                normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    def _detect_indent_style(self, code):
        """Detect if code uses tabs or spaces for indentation"""
        lines = code.split('\n')
        tab_count = 0
        space_count = 0
        
        for line in lines:
            if line.startswith('\t'):
                tab_count += 1
            elif line.startswith(' '):
                space_count += 1
        
        return 'tabs' if tab_count > space_count else 'spaces'
