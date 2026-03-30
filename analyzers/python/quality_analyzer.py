from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from radon.raw import analyze
import re

class QualityAnalyzer:
    def analyze(self, code, language):
        """
        Perform static analysis to evaluate code quality
        Returns metrics and detected issues
        """
        result = {
            'metrics': {},
            'code_smells': [],
            'style_issues': []
        }
        
        if language == 'python':
            result['metrics'] = self._analyze_python_metrics(code)
            result['code_smells'] = self._detect_python_smells(code)
            result['style_issues'] = self._check_python_style(code)
        else:
            result['metrics'] = self._analyze_generic_metrics(code)
            result['code_smells'] = self._detect_generic_smells(code)
        
        return result
    
    def _analyze_python_metrics(self, code):
        """Calculate Python-specific metrics using radon"""
        metrics = {
            'raw_metrics': {},
            'complexity': [],
            'maintainability_index': None,
            'halstead': {}
        }
        
        try:
            raw = analyze(code)
            actual_loc = len(code.splitlines())
            metrics['raw_metrics'] = {
                'loc': actual_loc,  
                'sloc': raw.sloc, 
                'comments': raw.comments,
                'blank': raw.blank,
                'multi': raw.multi 
            }
            print(f"\n✓ Raw metrics calculated by Radon:")
            print(f"   LOC (total): {raw.loc}")
            print(f"   SLOC (source): {raw.sloc}")
            print(f"   Blank: {raw.blank}")
            print(f"   Comments: {raw.comments}")
            print(f"   Math check: {raw.sloc} + {raw.blank} + {raw.comments} = {raw.sloc + raw.blank + raw.comments}")
            
            try:
                cc_results = cc_visit(code)
                print(f"✓ Complexity results: {cc_results}")
                for item in cc_results:
                    metrics['complexity'].append({
                        'name': item.name,
                        'complexity': item.complexity,
                        'rank': item.rank, 
                        'type': item.classname if hasattr(item, 'classname') else 'function'
                    })
                print(f"✓ Complexity data prepared: {metrics['complexity']}")
            except Exception as cc_error:
                print(f"✗ Complexity calculation failed: {cc_error}")
                metrics['complexity'] = []
            
            try:
                mi_score = mi_visit(code, multi=True)
                print(f"✓ MI score from Radon: {mi_score}")
                metrics['maintainability_index'] = round(mi_score, 2) if mi_score else None
                print(f"✓ Final MI: {metrics['maintainability_index']}")
            except Exception as mi_error:
                print(f"✗ MI calculation failed: {mi_error}")
                metrics['maintainability_index'] = None
            
            try:
                h_results = h_visit(code)
                if h_results:
                    metrics['halstead'] = {
                        'vocabulary': h_results.total.vocabulary,
                        'length': h_results.total.length,
                        'difficulty': round(h_results.total.difficulty, 2),
                        'effort': round(h_results.total.effort, 2)
                    }
            except Exception as h_error:
                print(f"⚠ Halstead calculation failed: {h_error}")
                pass
        
        except Exception as e:
            print(f"✗ CRITICAL: Quality analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            metrics['error'] = f"Failed to calculate metrics: {str(e)}"
        
        return metrics
    
    def _detect_python_smells(self, code):
        """Detect common Python code smells"""
        smells = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if len(line) > 100:
                smells.append({
                    'line': i,
                    'type': 'long_line',
                    'severity': 'low',
                    'message': f'Line exceeds 100 characters ({len(line)} chars)'
                })
            
            if ';' in stripped and not stripped.startswith('#'):
                smells.append({
                    'line': i,
                    'type': 'multiple_statements',
                    'severity': 'medium',
                    'message': 'Multiple statements on one line'
                })
            
            if re.match(r'except\s*:', stripped):
                smells.append({
                    'line': i,
                    'type': 'bare_except',
                    'severity': 'medium',
                    'message': 'Bare except clause catches all exceptions'
                })
            
            if 'TODO' in stripped or 'FIXME' in stripped:
                smells.append({
                    'line': i,
                    'type': 'todo_comment',
                    'severity': 'low',
                    'message': 'TODO/FIXME comment found'
                })
        
        global_pattern = re.compile(r'^([A-Z_][A-Z0-9_]*)\s*=')
        for i, line in enumerate(lines, 1):
            match = global_pattern.match(line)
            if match:
                var_name = match.group(1)
                smells.append({
                    'line': i,
                    'type': 'global_variable',
                    'severity': 'low',
                    'message': f'Problem: Global variable "{var_name}" detected at the file level.\nSuggestion: If this is meant to be a constant, it is perfectly fine. However, if this is a mutable variable, consider encapsulating it inside a class or passing it as an argument to prevent unwanted side-effects.'
                })
        
        try:
            import ast
            tree = ast.parse(code)
            
            defined_functions = {}
            called_functions = set()
            
            class AdvancedQualityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.loop_depth = 0
                    
                def visit_FunctionDef(self, node):
                    if node.name in defined_functions:
                        smells.append({
                            'line': node.lineno,
                            'type': 'duplicate_function',
                            'severity': 'high',
                            'message': f'Problem: Duplicate function definition detected for "{node.name}".\nSuggestion: Keep only one unique definition of this function to prevent unexpected runtime overrides.'
                        })
                    else:
                        defined_functions[node.name] = node
                        
                    func_length = getattr(node, 'end_lineno', node.lineno) - node.lineno
                    
                    has_loop = any(isinstance(n, (ast.For, ast.While, ast.AsyncFor)) for n in ast.walk(node))
                    has_calc = any(isinstance(n, (ast.BinOp, ast.AugAssign)) for n in ast.walk(node))
                    has_print = any(isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'print' for n in ast.walk(node))
                    
                    if func_length > 30 or (has_loop and has_calc and has_print):
                        smells.append({
                            'line': node.lineno,
                            'type': 'god_function',
                            'severity': 'medium',
                            'message': f'Problem: Function "{node.name}" is performing multiple responsibilities.\nSuggestion: Consider splitting this into smaller, more modular functions (e.g., separate the calculations from the printing).'
                        })
                        
                    self.generic_visit(node)
                    
            
            visitor = AdvancedQualityVisitor()
            visitor.visit(tree)
            
            for func_name, node in defined_functions.items():
                if func_name not in called_functions and not func_name.startswith('__'):
                    if func_name != 'main':
                        smells.append({
                            'line': node.lineno,
                            'type': 'unused_function',
                            'severity': 'medium',
                            'message': f'Problem: Unused function "{func_name}" is declared but never called.\nSuggestion: Consider removing this dead code or ensure it is properly utilized.'
                        })
                        
        except SyntaxError:
            pass # Invalid python code skips AST analysis safely
        except Exception as e:
            pass
            
        return smells
    
    def _check_python_style(self, code):
        """Check Python style conventions (PEP 8 style)"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if line.endswith(' ') or line.endswith('\t'):
                issues.append({
                    'line': i,
                    'type': 'trailing_whitespace',
                    'message': 'Trailing whitespace'
                })
            
            if '\t' in line:
                issues.append({
                    'line': i,
                    'type': 'tabs_used',
                    'message': 'Tab character used, PEP 8 recommends spaces'
                })
            
            func_match = re.match(r'def\s+([A-Z]\w+)\s*\(', line.strip())
            if func_match:
                issues.append({
                    'line': i,
                    'type': 'naming_convention',
                    'message': f'Function name "{func_match.group(1)}" should be lowercase with underscores'
                })
            
            class_match = re.match(r'class\s+([a-z_]\w+)', line.strip())
            if class_match:
                issues.append({
                    'line': i,
                    'type': 'naming_convention',
                    'message': f'Class name "{class_match.group(1)}" should use CapWords convention'
                })
        
        return issues
    
    def _analyze_generic_metrics(self, code):
        lines = code.split('\n')
        
        metrics = {
            'raw_metrics': {
                'total_lines': len(lines),
                'non_empty_lines': sum(1 for line in lines if line.strip()),
                'comment_lines': 0,
                'blank_lines': sum(1 for line in lines if not line.strip())
            },
            'average_line_length': 0
        }
        
        non_empty = [line for line in lines if line.strip()]
        if non_empty:
            metrics['average_line_length'] = round(sum(len(line) for line in non_empty) / len(non_empty), 1)
        
        return metrics
    
    def _detect_generic_smells(self, code):
        smells = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Very long lines
            if len(line) > 120:
                smells.append({
                    'line': i,
                    'type': 'long_line',
                    'severity': 'low',
                    'message': f'Line exceeds 120 characters ({len(line)} chars)'
                })
            
            if re.search(r'\b(?!0\b|1\b|-1\b)\d{2,}\b', line):
                smells.append({
                    'line': i,
                    'type': 'magic_number',
                    'severity': 'low',
                    'message': 'Magic number detected, consider using a named constant'
                })
        
        return smells
import ast

class SecurityAnalyzer:
    def __init__(self):
        self.secret_keywords = ['password', 'secret', 'token', 'api_key', 'auth', 'credentials']

    def analyze(self, code, language):
        issues = []
        if language != 'python':
            return {'issues': issues, 'score': 100, 'status': 'Unknown'}

        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        issues.append({
                            'type': 'Code Injection',
                            'severity': 'high',
                            'message': f"Use of {node.func.id}() is highly dangerous and can execute arbitrary malicious code.",
                            'line': node.lineno
                        })
                if isinstance(node, ast.JoinedStr):
                    for val in node.values:
                        if isinstance(val, ast.Constant) and isinstance(val.value, str):
                            if 'SELECT' in val.value.upper() or 'INSERT' in val.value.upper() or 'UPDATE' in val.value.upper():
                                issues.append({
                                    'type': 'SQL Injection Risk',
                                    'severity': 'high',
                                    'message': "Using f-strings for SQL queries is vulnerable to SQL Injection. Use parameterized SQL bindings (?, ?).",
                                    'line': node.lineno
                                })
        except:
            pass

        issues_count = len(issues)

        return {
            'issues': issues,
            'issues_count': issues_count
        }
