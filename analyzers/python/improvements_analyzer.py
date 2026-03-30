
import ast
import re

class ImprovementsAnalyzer:
    def __init__(self):
        pass
    
    def analyze(self, code, language, structure, naming_analysis, quality_analysis):
        """
        Generate human-readable improvement suggestions
        Does NOT modify code - only provides recommendations
        """
        suggestions = []
        
        if language == 'python':
            suggestions = self._analyze_python_improvements(
                code, structure, naming_analysis, quality_analysis
            )
        
        return {
            'suggestions': suggestions,
            'total_count': len(suggestions)
        }
    
    def _analyze_python_improvements(self, code, structure, naming_analysis, quality_analysis):
        """Generate improvement suggestions for Python code"""
        suggestions = []
        
        for func in structure.get('functions', []):
            func_name = func['name']
            
            if func_name == '__init__' or 'Constructor' in func_name:
                pass 
            elif not re.match(r'^[a-z_][a-z0-9_]*$', func_name) and not func_name.startswith('__'):
                snake_name = self._to_snake_case(func_name)
                suggestions.append({
                    'type': 'naming',
                    'severity': 'low',
                    'category': 'Code Style',
                    'suggestion': f"Rename function '{func_name}' to '{snake_name}' for better readability",
                    'line': func.get('line_start', 0)
                })
            
            if not func.get('docstring'):
                suggestions.append({
                    'type': 'documentation',
                    'severity': 'low',
                    'category': 'Documentation',
                    'suggestion': f"Function '{func_name}' can be documented using a docstring to explain its purpose",
                    'line': func.get('line_start', 0)
                })
        
        if naming_analysis and naming_analysis.get('suggestions'):
            similar_vars = self._find_related_variables(naming_analysis['suggestions'])
            
            if similar_vars:
                for group in similar_vars:
                    var_names = ', '.join([f"'{v}'" for v in group])
                    suggestions.append({
                        'type': 'refactoring',
                        'severity': 'medium',
                        'category': 'Code Organization',
                        'suggestion': f"Consider grouping related variables {var_names} into a list or dictionary for better organization"
                    })
        
        if quality_analysis:
            complexity = quality_analysis.get('cyclomatic_complexity', 0)
            
            if complexity > 10:
                suggestions.append({
                    'type': 'complexity',
                    'severity': 'medium',
                    'category': 'Code Quality',
                    'suggestion': f"Function complexity is {complexity}, consider breaking down into smaller functions"
                })
        
        if quality_analysis:
            total_lines = quality_analysis.get('total_lines', 0)
            comment_lines = quality_analysis.get('comment_lines', 0)
            
            if total_lines > 20 and comment_lines == 0:
                suggestions.append({
                    'type': 'documentation',
                    'severity': 'low',
                    'category': 'Documentation',
                    'suggestion': "No comments found. Consider adding comments to explain complex logic"
                })
        
        for func in structure.get('functions', []):
            line_start = func.get('line_start', 0)
            line_end = func.get('line_end', 0)
            func_length = line_end - line_start
            
            if func_length > 50:
                suggestions.append({
                    'type': 'refactoring',
                    'severity': 'medium',
                    'category': 'Code Organization',
                    'suggestion': f"Function '{func['name']}' is {func_length} lines long. Consider breaking it into smaller, focused functions",
                    'line': line_start
                })
        
        magic_numbers = self._detect_magic_numbers(code)
        for number, line in magic_numbers:
            suggestions.append({
                'type': 'maintainability',
                'severity': 'low',
                'category': 'Code Quality',
                'suggestion': f"Consider extracting magic number '{number}' at line {line} into a named constant",
                'line': line
            })
        
        if quality_analysis:
            mi = quality_analysis.get('maintainability_index')
            if mi is not None:
                if mi < 60:
                    suggestions.append({
                        'type': 'maintainability',
                        'severity': 'high',
                        'category': 'Maintainability',
                        'suggestion': f"Maintainability Index is {mi:.0f} (poor). Consider refactoring for better code maintainability: reduce complexity, add comments, and improve naming"
                    })
                elif mi < 80:
                    suggestions.append({
                        'type': 'maintainability',
                        'severity': 'medium',
                        'category': 'Maintainability',
                        'suggestion': f"Maintainability Index is {mi:.0f} (moderate). To improve: add more comments, reduce function complexity, and use clearer variable names"
                    })
        
        total_functions = len(structure.get('functions', []))
        total_classes = len(structure.get('classes', []))
        
        if total_functions > 10:
            suggestions.append({
                'type': 'modularity',
                'severity': 'medium',
                'category': 'Modularity',
                'suggestion': f"Code contains {total_functions} functions. Consider organizing into classes or separate modules for better modularity"
            })
        
        if total_classes == 0 and total_functions > 5:
            suggestions.append({
                'type': 'modularity',
                'severity': 'low',
                'category': 'Modularity',
                'suggestion': "Consider grouping related functions into classes to improve code organization and modularity"
            })
        
        return suggestions
    
    def _detect_magic_numbers(self, code):
        magic_numbers = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    if node.value in [0, 1, -1, 2, 10, 100, 1000]:
                        continue
                    
                    magic_numbers.append((node.value, node.lineno))
        
        except:
            pass
        
        return magic_numbers[:3]
    
    def _to_snake_case(self, name):
        """Convert name to snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
