"""
Code Analyzer - Step 5 & 6: Extract structure and validate consistency
"""
import ast
import re

class CodeAnalyzer:
    def extract_structure(self, code, language):
        """
        Extract code structure including functions, classes, and relationships
        """
        if language == 'python':
            return self._extract_python_structure(code)
        else:
            return self._extract_generic_structure(code)
    
    def _extract_python_structure(self, code):
        """Extract structure from Python code using AST"""
        structure = {
            'functions': [],
            'classes': [],
            'imports': [],
            'complexity_indicators': {
                'max_nesting_depth': 0,
                'large_functions': [],
                'deeply_nested_blocks': []
            },
            'call_graph': {}
        }
        
        try:
            tree = ast.parse(code)
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        structure['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        structure['imports'].append(f"{module}.{alias.name}")
            
            seen_functions = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self._analyze_function(node, code)
                    
                    if func_info['original_name'] not in seen_functions:
                        structure['functions'].append(func_info)
                        seen_functions.add(func_info['original_name'])
                    
                    if func_info['lines_count'] > 50:
                        structure['complexity_indicators']['large_functions'].append({
                            'name': func_info['name'],
                            'lines': func_info['lines_count']
                        })
                    
                    if func_info['max_nesting'] > 4:
                        structure['complexity_indicators']['deeply_nested_blocks'].append({
                            'name': func_info['name'],
                            'depth': func_info['max_nesting']
                        })
                    
                    structure['complexity_indicators']['max_nesting_depth'] = max(
                        structure['complexity_indicators']['max_nesting_depth'],
                        func_info['max_nesting']
                    )
                
                elif isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node, code)
                    structure['classes'].append(class_info)
            
            structure['call_graph'] = self._build_call_graph(tree)
        
        except Exception as e:
            structure['error'] = f"Failed to parse: {str(e)}"
        
        return structure
    
    def _analyze_function(self, node, code, is_method=False):
        """Analyze a single function"""
        lines = code.split('\n')
        
        name = node.name
        human_name = 'Constructor (__init__)' if name == '__init__' else name
        
        has_print = False
        magic_numbers_count = 0
        db_queries = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and getattr(child.func, 'id', '') == 'print':
                has_print = True
            elif isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                if child.value not in (-1, 0, 1, 2):  # Ignore common small constants
                    magic_numbers_count += 1
            if isinstance(child, ast.Call) and getattr(child.func, 'attr', '') in ('execute', 'query', 'commit', 'fetchall'):
                db_queries = True
                
        docstring = ast.get_docstring(node)
        has_docstring = bool(docstring)
        if not docstring:
            clean_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ').strip().lower()
            if name == '__init__':
                docstring = "Initializes the object instance and sets up required attributes."
            elif db_queries:
                docstring = "Interacts with the database to fetch or update records."
            elif has_print and ('calc' in name or 'compute' in name):
                docstring = "Processes calculations and displays the computed results."
            elif clean_name.startswith('get '):
                docstring = f"Retrieves and returns the {clean_name[4:]} data."
            elif clean_name.startswith('set '):
                docstring = f"Validates and modifies the {clean_name[4:]} value."
            elif clean_name.startswith('is '):
                docstring = f"Evaluates if the current state {clean_name[3:]}."
            else:
                words = clean_name.split()
                if words and not words[0].endswith('s') and not words[0].endswith('ed'):
                    words[0] = words[0] + 's'
                docstring = f"Executes the {' '.join(words)} operation based on application logic."
        
        params = [arg.arg for arg in node.args.args if arg.arg != 'self' or not is_method]
        
        max_nesting = self._calculate_nesting_depth(node)
        lines_count = (node.end_lineno if hasattr(node, 'end_lineno') else node.lineno) - node.lineno + 1
        calls = self._extract_function_calls(node)
        
        warnings = []
        if not has_docstring:
            warnings.append({
                "category": "Best Practice",
                "issue": f"Function '{name}' lacks documentation",
                "why": "Makes code harder for other developers to understand",
                "fix": "Add a descriptive docstring explaining purpose and parameters"
            })
            
        if lines_count > 50:
            warnings.append({
                "category": "Structural",
                "issue": f"Function '{name}' is too long ({lines_count} lines)",
                "why": "Harder to maintain, test, and understand",
                "fix": "Extract logical blocks into smaller helper functions"
            })
        if max_nesting > 3:
            warnings.append({
                "category": "Readability",
                "issue": f"Deep nesting detected in '{name}'",
                "why": "Makes control flow difficult to follow",
                "fix": "Use early returns (guard clauses) to reduce nesting"
            })
        if magic_numbers_count > 2:
            warnings.append({
                "category": "Best Practice",
                "issue": f"Magic numbers used in '{name}'",
                "why": "Raw numbers lack context and make future changes error-prone",
                "fix": "Extract numbers into named ALL_CAPS constants"
            })
        if len(calls) > 6:
            warnings.append({
                "category": "Structural",
                "issue": f"Multiple responsibilities detected in '{name}'",
                "why": "Function performs too many different operations",
                "fix": "Split into distinct functions following Single Responsibility Principle"
            })
            
        returns = self._extract_returns(node)
        human_returns = []
        for r in returns:
            if r == 'variable': human_returns.append('Returns the calculated result based on input values')
            elif r == 'dict': human_returns.append('Returns a structured dictionary mapping')
            elif r == 'list': human_returns.append('Yields a collection or array of items')
            elif r == 'tuple': human_returns.append('Provides an immutable sequence of elements')
            elif r == 'Call Result': human_returns.append('Passes through the result of an internal pipeline')
            elif r == 'complex expression': human_returns.append('Returns a dynamically evaluated expression')
            elif r == 'Unknown': human_returns.append('Produces a varying or dynamically typed outcome')
            elif r == 'None': human_returns.append('Performs operation without returning a value (Void)')
            else: human_returns.append(f'Returns a {r} instance/primitive')
        
        func_info = {
            'name': human_name,
            'original_name': name,
            'line_start': node.lineno,
            'line_end': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            'lines_count': lines_count,
            'params': params,
            'docstring': docstring,
            'has_docstring': has_docstring,
            'returns': list(set(human_returns)),
            'warnings': warnings,
            'max_nesting': max_nesting,
            'calls': calls
        }
        
        return func_info
    
    def _extract_returns(self, node):
        returns = []
        has_return = False
        
        # Check type hint first
        if getattr(node, 'returns', None):
            if hasattr(node.returns, 'id'):
                returns.append(node.returns.id)
            elif hasattr(node.returns, 'value') and hasattr(node.returns.value, 'id'):
                returns.append(node.returns.value.id)
        
        if not returns:
            for child in ast.walk(node):
                if isinstance(child, ast.Return):
                    has_return = True
                    if child.value:
                        if isinstance(child.value, ast.Constant):
                            returns.append(type(child.value.value).__name__)
                        elif isinstance(child.value, ast.Name):
                            returns.append('variable')
                        elif isinstance(child.value, ast.Dict):
                            returns.append('dict')
                        elif isinstance(child.value, ast.List):
                            returns.append('list')
                        elif isinstance(child.value, ast.Tuple):
                            returns.append('tuple')
                        elif isinstance(child.value, ast.Call):
                            returns.append('Call Result')
                        else:
                            returns.append('complex expression')
                    else:
                        returns.append('None')
        
        if not returns and has_return:
            return ["Unknown"]
        elif not returns and not has_return:
            return ["None"]
        
        return list(set(returns))
    
    def _analyze_class(self, node, code):
        methods = []
        all_warnings = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_function(item, code, is_method=True)
                methods.append(method_info)
                all_warnings.extend(method_info.get('warnings', []))
        
        name = node.name
        docstring = ast.get_docstring(node)
        has_docstring = bool(docstring)
        if not docstring:
            clean_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).strip()
            init_method = next((m for m in methods if m['original_name'] == '__init__'), None)
            if init_method and init_method['params']:
                params_str = ", ".join(init_method['params'])
                docstring = f"Represents a core {clean_name} model implementing logic around {params_str}."
            else:
                docstring = f"Represents a structural {clean_name} blueprint outlining associated behaviors."
            
        warnings = []
        if not has_docstring:
            warnings.append({
                "category": "Best Practice",
                "issue": f"Class '{name}' lacks documentation",
                "why": "Future developers won't know the intended use of this class",
                "fix": "Add a class-level docstring describing its responsibility"
            })
        if len(name) < 3:
            warnings.append({
                "category": "Naming",
                "issue": f"Class name '{name}' is unclear",
                "why": "Short names obscure the entity represented",
                "fix": "Rename to a descriptive noun (e.g., UserAccount)"
            })
            
        class_info = {
            'name': name,
            'line_start': node.lineno,
            'line_end': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            'methods': methods,
            'docstring': docstring,
            'has_docstring': has_docstring,
            'warnings': warnings
        }
        
        return class_info
    
    def _calculate_nesting_depth(self, node, current_depth=0):
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _extract_function_calls(self, node):
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        
        return list(set(calls))
    
    def _build_call_graph(self, tree):
        call_graph = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                calls = self._extract_function_calls(node)
                call_graph[node.name] = calls
        
        return call_graph
    
    def _extract_generic_structure(self, code):
        structure = {
            'functions': [],
            'classes': [],
            'complexity_indicators': {
                'max_nesting_depth': 0,
                'large_functions': []
            }
        }
        
        func_pattern = r'(?:function|def|public|private|protected)?\s*(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*\{'
        matches = re.finditer(func_pattern, code)
        
        for match in matches:
            func_name = match.group(1)
            start_pos = match.start()
            
            params_str = ""
            param_match = re.search(func_name + r'\s*\((.*?)\)', code[start_pos:])
            if param_match:
                params_str = param_match.group(1)
            params = [p.strip() for p in params_str.split(',')] if params_str.strip() else []
            
            
            brace_count = 1
            pos = match.end()
            while pos < len(code) and brace_count > 0:
                if code[pos] == '{':
                    brace_count += 1
                elif code[pos] == '}':
                    brace_count -= 1
                pos += 1
            
            func_code = code[start_pos:pos]
            lines_count = func_code.count('\n')
            
            if lines_count > 50:
                structure['complexity_indicators']['large_functions'].append({
                    'name': func_name,
                    'lines': lines_count
                })
        
        class_pattern = r'class\s+(\w+)'
        class_matches = re.finditer(class_pattern, code)
        
        for match in class_matches:
            structure['classes'].append({
                'name': match.group(1)
            })
        
        return structure
    
    def validate_consistency(self, structure, intent_analysis):
        """
        Step 6: Validate consistency between structure and intent
        """
        issues = []
        
        for func in structure.get('functions', []):
            if 'calls' in func and len(func['calls']) > 10:
                issues.append({
                    'type': 'multiple_responsibilities',
                    'severity': 'medium',
                    'location': f"Function '{func['name']}'",
                    'description': f"Function calls {len(func['calls'])} different functions, may have multiple responsibilities"
                })
            
            if func.get('lines_count', 0) > 100:
                issues.append({
                    'type': 'large_function',
                    'severity': 'medium',
                    'location': f"Function '{func['name']}'",
                    'description': f"Function is {func['lines_count']} lines long, consider breaking it down"
                })
        
        for item in structure.get('complexity_indicators', {}).get('deeply_nested_blocks', []):
            issues.append({
                'type': 'deep_nesting',
                'severity': 'high',
                'location': f"Function '{item['name']}'",
                'description': f"Nesting depth of {item['depth']} detected, may reduce readability"
            })
        
        return {
            'has_issues': len(issues) > 0,
            'issues_count': len(issues),
            'issues': issues
        }
