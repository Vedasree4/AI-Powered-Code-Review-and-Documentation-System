import ast

class PerformanceAnalyzer:
    def analyze(self, code, language):
        if language != 'python':
            return {'complexity': 'Unknown', 'suggestions': []}

        max_depth = 0
        suggestions = []

        class LoopVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0

            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

        try:
            tree = ast.parse(code)
            visitor = LoopVisitor()
            visitor.visit(tree)
            max_depth = visitor.max_depth

            # Detect O(N) Array Lookups that should be Hash Maps
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for op in node.ops:
                        if isinstance(op, ast.In):
                            if isinstance(node.comparators[0], ast.List):
                                suggestions.append({
                                    'message': "Found lookup `x in [...]`. Arrays have O(N) lookup complexity. Convert this to a Set `{...}` for instantaneous O(1) performance.",
                                    'line': node.lineno
                                })
        except:
            pass

        complexity = "O(1) Constant"
        if max_depth == 1: complexity = "O(N) Linear"
        elif max_depth == 2: complexity = "O(N²) Quadratic"
        elif max_depth >= 3: complexity = f"O(N^{max_depth}) Polynomial"

        if max_depth >= 2:
            suggestions.append({
                'message': f"Detected {max_depth} nested loops resulting in {complexity} mathematical time complexity. Code will exponentially lag on larger datasets. Consider using a Hash Map or Vectorization via Pandas.",
                'line': 0
            })

        return {
            'complexity': complexity,
            'suggestions': suggestions
        }
