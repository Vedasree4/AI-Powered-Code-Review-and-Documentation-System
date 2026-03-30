import re
import math

class JavaAnalyzer:
    def analyze(self, code, problem_statement=""):
        lines = code.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        
        comment_lines = 0
        in_multiline_comment = False
        for line in lines:
            stripped = line.strip()
            if in_multiline_comment:
                comment_lines += 1
                if '*/' in stripped:
                    in_multiline_comment = False
            elif stripped.startswith('/*'):
                comment_lines += 1
                if '*/' not in stripped:
                    in_multiline_comment = True
            elif stripped.startswith('//'):
                comment_lines += 1
                
        source_lines = total_lines - blank_lines - comment_lines
        
        # Heuristic cyclomatic complexity
        cc = 1 + len(re.findall(r'\b(if|for|while|case|catch)\b', code))
        
        mi = 100.0
        if source_lines > 0:
            v = source_lines * 4.5
            v_log = math.log(v) if v > 0 else 0
            loc_log = math.log(source_lines) if source_lines > 0 else 0
            mi_raw = 171 - 5.2 * v_log - 0.23 * cc - 16.2 * loc_log
            mi = max(0.0, min(100.0, (mi_raw * 100) / 171.0))
        mi = round(mi, 2)
        
        result = {
            "summary": {
                "total_lines": total_lines,
                "functions": 0,
                "constructors": 0,
                "classes": 0,
                "maintainability_index": mi
            },
            "metrics": {
                "total_lines": total_lines,
                "source_lines": source_lines,
                "comment_lines": comment_lines,
                "blank_lines": blank_lines,
                "maintainability_index": mi
            },
            "identifiers": {
                "total": 0,
                "good": 0,
                "needs_improvement": 0
            },
            "naming_issues": [],
            "code_quality_issues": [],
            "documentation": {
                "classes": [],
                "functions": [],
                "constructors": []
            },
            "improvements": [],
            "performance_analysis": {
                "complexity": "O(1) Constant",
                "suggestions": []
            },
            "security_analysis": {
                "issues": []
            }
        }
        
        # 4. Code Quality Analysis
        self._analyze_quality(lines, result["code_quality_issues"])
        
        # Calculate Performance Complexity based on nested loops in quality issues
        max_loop_depth = 0
        for issue in result["code_quality_issues"]:
            if issue["type"] == "nested_loop":
                # Very basic heuristic: if we flag it, it's at least O(N^2)
                # Let's count indents to be smarter
                line_text = lines[int(issue["line"]) - 1]
                indent = len(line_text) - len(line_text.lstrip())
                depth = (indent // 4) + 1 # assuming 4 space indents
                max_loop_depth = max(max_loop_depth, depth)
            elif "for" in code or "while" in code:
                max_loop_depth = max(max_loop_depth, 1)

        comp = "O(1) Constant"
        if max_loop_depth == 1: comp = "O(N) Linear"
        elif max_loop_depth == 2: comp = "O(N²) Quadratic"
        elif max_loop_depth >= 3: comp = f"O(N^{max_loop_depth}) Polynomial"
        result["performance_analysis"]["complexity"] = comp

        if max_loop_depth >= 2:
            result["performance_analysis"]["suggestions"].append({
                "message": f"Detected {max_loop_depth} nested loops. Java execution will grow exponentially with input. Consider using a Map or Stream API optimization.",
                "line": 0
            })
            
        # Basic Security for Java
        if "System.getProperty" in code or "Runtime.getRuntime().exec" in code:
            result["security_analysis"]["issues"].append({
                "type": "Runtime Execution",
                "severity": "high",
                "message": "Direct OS command execution detected. Highly dangerous if input is untrusted.",
                "line": 0
            })
        if "DriverManager.getConnection" in code and ("password" in code.lower() or "pwd" in code.lower()):
            result["security_analysis"]["issues"].append({
                "type": "Potential Secret Leak",
                "severity": "high",
                "message": "Database connection with hardcoded credentials detected.",
                "line": 0
            })

        seen_identifiers = set()
        
        # KEYWORDS to ignore for identifier extraction
        java_keywords = set([
            "abstract", "continue", "for", "new", "switch", "assert", "default", "goto", "package", "synchronized",
            "boolean", "do", "if", "private", "this", "break", "double", "implements", "protected", "throw",
            "byte", "else", "import", "public", "throws", "case", "enum", "instanceof", "return", "transient",
            "catch", "extends", "int", "short", "try", "char", "final", "interface", "static", "void",
            "class", "finally", "long", "strictfp", "volatile", "const", "float", "native", "super", "while",
            "true", "false", "null", "String", "Object", "System", "out", "println"
        ])
        
        # 1. Classes and 2. Methods/Constructors
        class_pattern = re.compile(r'\b(?:class|interface|enum)\s+([A-Za-z0-9_]+)', re.MULTILINE)
        method_pattern = re.compile(r'^\s*(?:(?:public|protected|private|static|final|abstract|synchronized|native|strictfp|\@\w+(?:\([^)]*\))?)\s+)*([\w\.\[\]<>]+)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*(?:throws\s+[a-zA-Z0-9_,\s]+)?\s*[{;]', re.MULTILINE)
        constructor_pattern = re.compile(r'^\s*(?:(?:public|protected|private)\s+)*([A-Z][a-zA-Z0-9_]*)\s*\((.*?)\)\s*(?:throws\s+[A-Za-z0-9_,\s]+)?\s*\{', re.MULTILINE)
        
        classes_parsed = []
        for match in class_pattern.finditer(code):
            class_name = match.group(1)
            classes_parsed.append({
                "name": class_name,
                "start": match.start(),
                "methods": [],
                "docstring": f"Purpose: Blueprint structure for {class_name} representing its core state and behaviors."
            })
            
            result["summary"]["classes"] += 1
            if class_name in seen_identifiers: continue
            seen_identifiers.add(class_name)
            
            # Check PascalCase
            is_valid = True
            if not class_name[0].isupper() or '_' in class_name:
                is_valid = False
            if len(class_name) < 3:
                is_valid = False
                    
            if not is_valid:
                result["identifiers"]["needs_improvement"] += 1
                result["naming_issues"].append({
                    "category": "Naming Violations",
                    "issue": f"Suboptimal class name '{class_name}'",
                    "location": f"Class: {class_name}",
                    "current_name": class_name,
                    "suggestion": class_name.capitalize(),
                    "description": f"The class name '{class_name}' does not follow standard conventions. It should clearly identify the blueprint's purpose.",
                    "type": "class",
                    "reason": "Class names must use PascalCase (e.g., UserAccount) to be perfectly distinguishable from instances, immediately signaling it is a type definition.",
                    "why": f"Java classes must use PascalCase.",
                    "fix": f"Suggestion: Rename to '{class_name.capitalize()}'"
                })
                
        # Context-Aware Keyword Extraction
        context_words = re.findall(r'\b[a-zA-Z]{3,}\b', problem_statement.lower()) if problem_statement else []
        ignore_words = {'this', 'that', 'the', 'and', 'with', 'for', 'from', 'when', 'how', 'what', 'who', 'function', 'class', 'code', 'program', 'variable', 'method', 'calculate', 'compute', 'find', 'get', 'set'}
        meaningful_words = [w for w in context_words if w not in ignore_words]
        context_keyword = meaningful_words[0] if meaningful_words else ""
                
        # Parse methods and constructors
        methods_parsed = []
        seen_methods = set()
        
        for match in method_pattern.finditer(code):
            ret_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params_str = match.group(3)
            pos = match.start()
            
            # Prevent regex backtracking from catching constructors as functions
            if ret_type in ("public", "private", "protected", "static", "final", "abstract", "synchronized", "native", "strictfp"):
                continue
            
            # Skip common false positives
            if method_name in ('if', 'for', 'while', 'switch', 'catch', 'return', 'new'): continue
                
            doc_string = f"Purpose: Executes operations for {method_name}. Return: {ret_type}"
            if method_name == "main" and "String[]" in params_str:
                doc_string = "Purpose: Main Program Entry Point."
                
            params = [p.strip() for p in params_str.split(',')] if params_str.strip() else []
            methods_parsed.append({
                "name": method_name,
                "params": params,
                "returns": [ret_type],
                "docstring": doc_string,
                "start": pos,
                "is_constructor": False
            })
            seen_methods.add(method_name)
            
        for match in constructor_pattern.finditer(code):
            method_name = match.group(1)
            params_str = match.group(2)
            pos = match.start()
            
            # Avoid duplication
            if method_name in seen_methods: continue
                
            params = [p.strip() for p in params_str.split(',')] if params_str.strip() else []
            methods_parsed.append({
                "name": method_name,
                "params": params,
                "returns": ["Constructor/Self"],
                "docstring": f"Purpose: Constructor initializing state for {method_name}.",
                "start": pos,
                "is_constructor": True
            })
            
        methods_parsed.sort(key=lambda x: x["start"])
        
        # Method Naming Generic mappings
        poor_method_names = {
            'dostuff': 'calculateSum / computeTotal',
            'processdata': 'transformInputData',
            'handle': 'manageRequestEvent',
            'run': 'executeTaskProcess'
        }
        
        # Validate method naming and assign to classes
        for method in methods_parsed:
            method_name = method["name"]
            
            # Assign methods to the nearest preceding class
            owner_class = None
            for cls in reversed(classes_parsed):
                if cls["start"] < method["start"]:
                    owner_class = cls
                    break
            
            # Exclude constructors from total function count and functions list as per requirement
            if not method["is_constructor"]:
                if owner_class:
                    owner_class["methods"].append(method)
                
                # Append to functions list ALWAYS (to ensure standalone & class methods are counted correctly)
                result["documentation"]["functions"].append(method)
                result["summary"]["functions"] += 1
            else:
                result["documentation"]["constructors"].append(method)
                result["summary"]["constructors"] += 1
            
            if method_name in seen_identifiers: continue
            if method["is_constructor"]: 
                seen_identifiers.add(method_name)
                continue # Constructors handled by class rules
                
            if method_name == "main":
                seen_identifiers.add(method_name)
                # Ignore main() for naming analysis
                continue
                
            seen_identifiers.add(method_name)
            
            # Check for generic/poor method names
            is_valid = True
            issue_desc = ""
            issue_reason = ""
            sugg = method_name.lower()
            
            lower_name = method_name.lower()
            if lower_name in poor_method_names:
                is_valid = False
                issue_desc = f"The method name '{method_name}' is too generic or confusing."
                issue_reason = "Other developers reading this won't know what it exactly does. A good method name operates as instant, readable documentation."
                sugg = poor_method_names[lower_name]
            else:
                # Check camelCase
                if not method_name.islower() and (not method_name[0].islower() or '_' in method_name):
                    if method_name != method_name.upper():  # Not a constant
                        is_valid = False
                        issue_desc = f"The method name '{method_name}' does not follow camelCase format."
                        issue_reason = "Consistency is key. Java tools and developers expect standard camelCase for methods. Breaking conventions increases cognitive load."
                        
                if len(method_name) < 3 and method_name not in ('id', 'to'):
                    is_valid = False
                    issue_desc = f"The method name '{method_name}' is extremely short and uninformative."
                    issue_reason = "Method names should be a descriptive action verb (e.g., 'saveUser' instead of 'sv'). Shorthand slows down codebase adoption."
                    
            if not is_valid:
                result["identifiers"]["needs_improvement"] += 1
                
                # Context integration for methods if applicable
                context_sugg = sugg
                if context_keyword and lower_name in poor_method_names:
                    context_sugg = f"{sugg.split(' / ')[0].replace('Data', context_keyword.capitalize())} / {sugg.split(' / ')[-1]}"
                
                result["naming_issues"].append({
                    "category": "Naming Violations",
                    "issue": f"Suboptimal method name '{method_name}'",
                    "location": f"Method: {method_name}",
                    "current_name": method_name,
                    "suggestion": context_sugg,
                    "description": issue_desc,
                    "type": "method",
                    "reason": issue_reason,
                    "why": issue_desc,
                    "fix": f"Action: Rename to a descriptive verb-noun pair, e.g., '{context_sugg}'"
                })
                
        # Transfer the linked classes to results
        for cls in classes_parsed:
            cls.pop("start", None)
            for m in cls["methods"]: m.pop("start", None)
            result["documentation"]["classes"].append(cls)
                    
        # 3. Comprehensive Identifiers / Variables
        # Instead of just type var_pattern, extract all words and filter
        all_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code)
        
        mapped_suggestions = {
            'res': 'totalSum / resultValue',
            'a': 'firstValue / inputValue',
            'b': 'secondValue / configData',
            'c': 'factor / thresholdLimit',
            'x': 'xCoordinate / horizontalIndex',
            'y': 'yCoordinate / verticalIndex',
            'z': 'thirdValue / inputZ',
            'temp': 'temporaryBuffer / cacheBlock',
            'val': 'currentValue / activeNode',
            'data': 'payloadData / userRecord',
            'obj': 'dataObject / modelEntity',
            'info': 'detailsInfo / activeMetadata',
            'list': 'userList / targetCollection'
        }
        
        for word in all_words:
            if word in java_keywords: continue
            if word in seen_identifiers: continue
            
            var_name = word
            seen_identifiers.add(var_name)
            
            # Check camelCase or ALL_CAPS
            is_valid = True
            issue_desc = f"The variable name '{var_name}' breaks camelCase convention."
            issue_reason = "Standard conventions allow developers to easily distinguish between constants, classes, and local variables."
            sugg = var_name.lower()
            
            if var_name.isupper() and '_' in var_name:
                pass # valid constant
            elif not var_name[0].islower() or '_' in var_name:
                if var_name != var_name.upper():
                    is_valid = False
            
            lower_name = var_name.lower()
            if len(var_name) < 3 and var_name not in ('i', 'j', 'k', 'n', 'e'):
                is_valid = False
                issue_desc = f"The variable '{var_name}' is too short and uninformative."
                issue_reason = "Single-letter variables are strictly for loop iterations. Using descriptive nouns saves teammates from having to reverse-engineer your code."
                
                base_sugg = mapped_suggestions.get(lower_name, f"input{var_name.capitalize()} / active{var_name.capitalize()}")
                if context_keyword:
                    sugg = f"{context_keyword.replace('_', '')}{base_sugg.split(' / ')[0].capitalize()} / {context_keyword}{var_name.capitalize()}"
                else:
                    sugg = base_sugg
                
            if lower_name in mapped_suggestions:
                is_valid = False
                issue_desc = f"The variable '{var_name}' is too generic."
                issue_reason = "Other developers won't instantly know what data this holds. Using a descriptive, precise name completely eliminates the need for comments."
                base_sugg = mapped_suggestions[lower_name]
                
                if context_keyword:
                    # Dynamically inject the known real-world problem context into the suggestion
                    sugg = f"{context_keyword}{base_sugg.split(' / ')[0].capitalize()} / {context_keyword}Result"
                else:
                    sugg = base_sugg
                
            if not is_valid:
                result["identifiers"]["needs_improvement"] += 1
                result["naming_issues"].append({
                    "category": "Naming Violations",
                    "issue": f"Unclear variable name '{var_name}'",
                    "location": f"Variable: {var_name}",
                    "current_name": var_name,
                    "suggestion": sugg,
                    "description": issue_desc,
                    "type": "variable",
                    "reason": issue_reason,
                    "why": issue_desc,
                    "fix": f"Action: Rename \"{var_name}\" to \"{sugg.split(' / ')[0]}\" or \"{sugg.split(' / ')[-1]}\""
                })
                
    
                
        # Final explicit logical consistency check to fulfill identifier counts:
        result["identifiers"]["total"] = len(seen_identifiers)
        result["identifiers"]["good"] = len(seen_identifiers) - result["identifiers"]["needs_improvement"]

        return result

    def _analyze_quality(self, lines, quality_issues):
        nested_loop_pattern = re.compile(r'\b(for|while)\b.*\b(for|while)\b')
        
        in_method = False
        method_length = 0
        method_start = 0
        current_method_name = ""
        nesting_level = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Readability: Deep Nesting Tracking
            nesting_level += line.count('{')
            nesting_level -= line.count('}')
            
            # Readability: Complex Logic
            if line.count('&&') + line.count('||') > 2:
                quality_issues.append({
                    "category": "Readability",
                    "issue": "Complex Logic Chain",
                    "description": "Too many logical operators (&&, ||) chained in a single line. This drastically hurts readability. Consider extracting logic into well-named boolean variables.",
                    "type": "complex_logic",
                    "severity": "medium",
                    "line": i
                })
                
            if nesting_level > 3 and '{' in line:
                quality_issues.append({
                    "category": "Readability",
                    "issue": "Deep Nesting",
                    "description": f"Logic is deeply nested (level {nesting_level}). High cyclomatic complexity makes edge cases extremely difficult to test and maintain.",
                    "type": "deep_nesting",
                    "severity": "high",
                    "line": i
                })
            
            # Magic Numbers
            magic_match = re.search(r'\b(?![012]\b)(\d{2,})\b', stripped)
            if magic_match:
                num = magic_match.group(1)
                quality_issues.append({
                    "category": "Code Smell",
                    "issue": "Magic Number",
                    "description": f"Hardcoded magic number '{num}' detected. Consider promoting this to a named constant (e.g., `final int MAX_LIMIT = {num};`) to explain its physical meaning.",
                    "type": "magic_number",
                    "severity": "low",
                    "line": i
                })
                
            # Nested Loops (simple heuristic: multiple loop keywords on one line or deep indentation)
            if nested_loop_pattern.search(line) or (line.startswith('            for') or line.startswith('\t\t\tfor')):
                quality_issues.append({
                    "category": "Performance / Complexity",
                    "issue": "Nested Loop",
                    "description": "Deeply nested loops significantly reduce readability and scale exponentially, risking performance degradation (O(n^2) time).",
                    "type": "nested_loop",
                    "severity": "medium",
                    "line": i
                })
                
            # Modularity: Long Methods (Heuristic)
            method_start_match = re.match(r'\b(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>\[\]]+\s+)?(\w+)\s*\(', stripped)
            if method_start_match:
                in_method = True
                method_length = 0
                method_start = i
                current_method_name = method_start_match.group(1)
            elif in_method:
                method_length += 1
                if stripped == '}':
                    if method_length > 25:
                        quality_issues.append({
                            "category": "Modularity",
                            "issue": "Excessively Long Method",
                            "description": f"The method '{current_method_name}' is violating the Single Responsibility Principle by being too massive ({method_length} lines). Splitting it into smaller, composable helper methods will vastly improve modularity.",
                            "type": "long_method",
                            "severity": "medium",
                            "line": method_start
                        })
                    in_method = False
