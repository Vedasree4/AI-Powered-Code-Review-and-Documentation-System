from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys
from analyzers.python.code_validator import CodeValidator
from analyzers.python.code_preprocessor import CodePreprocessor
from analyzers.python.code_analyzer import CodeAnalyzer
from analyzers.python.intent_analyzer import IntentAnalyzer
from analyzers.python.quality_analyzer import QualityAnalyzer
from analyzers.python.naming_analyzer import NamingAnalyzer
from analyzers.python.improvements_analyzer import ImprovementsAnalyzer
from analyzers.java.java_analyzer import JavaAnalyzer

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    """
    Main endpoint for code analysis
    Accepts code via file upload or direct text input
    """
    try:
        code = None
        problem_statement = request.form.get('problem_statement', '')
        
        # Check if code was uploaded as a file
        if 'code_file' in request.files:
            file = request.files['code_file']
            if file.filename != '':
                code = file.read().decode('utf-8')
        
        # If no file, check for pasted/typed code
        if not code:
            code = request.form.get('code', '')
        
        # Step 2: Validate that code is present
        if not code or code.strip() == '':
            return jsonify({
                'success': False,
                'error': 'No code provided. Please upload a file or paste/type your code.'
            }), 400
        
        # Strip trailing newlines/whitespace to match editor line count
        # This prevents invisible trailing lines from inflating LOC
        original_lines = len(code.splitlines())
        code = code.rstrip('\n\r ')
        stripped_lines = len(code.splitlines())
        
        # Get explicit language if any
        selected_language = request.form.get('language', 'python').lower()
        
        if selected_language == 'java':
            # --- JAVA ANALYSIS ---
            java_analyzer = JavaAnalyzer()
            java_res = java_analyzer.analyze(code, problem_statement)
            
            # 1. Map naming issues
            suggestions = []
            for issue in java_res.get("naming_issues", []):
                suggestions.append(issue)
                
            naming_summary = {
                "total_identifiers": java_res["identifiers"]["total"],
                "good_names_count": java_res["identifiers"]["good"],
                "poor_names_count": java_res["identifiers"]["needs_improvement"]
            }
                
            analysis_results = {
                'success': True,
                'language': 'java',
                'preprocessed_code': {'cleaned_code': code, 'original_lines': original_lines},
                'intent_analysis': {'purpose': 'Java Application Code', 'components': []},
                'structure_analysis': {
                    'classes': [],
                    'functions': []
                },
                'consistency_analysis': {'is_consistent': True, 'issues': []},
                'quality_analysis': {
                    'metrics': {
                        'raw_metrics': {
                            'loc': java_res["metrics"]["total_lines"],
                            'sloc': java_res["metrics"]["source_lines"],
                            'comments': java_res["metrics"]["comment_lines"],
                            'blank': java_res["metrics"]["blank_lines"]
                        }, 
                        'maintainability_index': java_res["metrics"]["maintainability_index"], 
                        'cyclomatic_complexity': 1
                    },
                    'code_smells': java_res.get("code_quality_issues", []),
                    'issues': []
                },
                'naming_analysis': {
                    'summary': naming_summary,
                    'suggestions': suggestions
                },
                'improvements_analysis': {'suggestions': java_res.get("improvements", [])},
                'performance_analysis': java_res.get("performance_analysis", {
                    'complexity': 'Unknown',
                    'suggestions': []
                }),
                'security_analysis': java_res.get("security_analysis", {
                    'issues': []
                }),
                'robustness_info': {
                    'has_functions': java_res["summary"]["functions"] > 0,
                    'has_classes': java_res["summary"]["classes"] > 0,
                    'has_problem_statement': bool(problem_statement),
                    'is_complete': True,
                    'messages': []
                }
            }
            
            # Decorate the classes and functions
            classes_list = []
            for c in java_res["documentation"]["classes"]:
                # Process methods within class to attach warnings
                methods = c.get("methods", [])
                for m in methods:
                    m["warnings"] = [w for w in suggestions if w["type"] == "method" and w["current_name"] == m["name"]]
                    
                classes_list.append({
                    "name": c["name"],
                    "docstring": c["docstring"],
                    "methods": methods,
                    "warnings": [w for w in suggestions if w["type"] == "class" and w["current_name"] == c["name"]]
                })
            analysis_results['structure_analysis']['classes'] = classes_list
            
            functions_list = []
            for f in java_res["documentation"]["functions"]:
                functions_list.append({
                    "name": f["name"],
                    "docstring": f["docstring"],
                    "params": f.get("params", []),
                    "returns": f.get("returns", []),
                    "warnings": [w for w in suggestions if w["type"] == "method" and w["current_name"] == f["name"]]
                })
            analysis_results['structure_analysis']['functions'] = functions_list
            
            return jsonify(analysis_results)
            
        else:
            # --- PYTHON ANALYSIS ---
            validator = CodeValidator()
            validation_result = validator.validate(code)
            
            if not validation_result['is_valid']:
                return jsonify({
                    'success': False,
                    'error': validation_result['error'],
                    'details': validation_result.get('details', [])
                }), 400
            
            detected_language = validation_result['language']
            
            # Step 3: Preprocess the code (using cleaned code)
            preprocessor = CodePreprocessor()
            preprocessed_code = preprocessor.preprocess(code, detected_language)
            
            # Step 4: Understand the purpose of the code
            intent_analyzer = IntentAnalyzer()
            intent_analysis = intent_analyzer.analyze(
                preprocessed_code['cleaned_code'],
                detected_language,
                problem_statement
            )
            
            # Step 5: Extract code structure and flow
            code_analyzer = CodeAnalyzer()
            structure_analysis = code_analyzer.extract_structure(
                preprocessed_code['cleaned_code'],
                detected_language
            )
            
            # Step 6: Validate intent and structure consistency
            consistency_analysis = code_analyzer.validate_consistency(
                structure_analysis,
                intent_analysis
            )
            
            # Step 7: Evaluate objective code quality
            quality_analyzer = QualityAnalyzer()
            quality_analysis = quality_analyzer.analyze(
                preprocessed_code['cleaned_code'],
                detected_language
            )
            
            # Step 8: Assess naming clarity and readability
            naming_analyzer = NamingAnalyzer()
            naming_analysis = naming_analyzer.analyze(
                preprocessed_code['cleaned_code'],
                detected_language,
                structure_analysis,
                problem_statement
            )
            
            # Step 9: Generate improvement suggestions (text-only, safe)
            improvements_analyzer = ImprovementsAnalyzer()
            improvements_analysis = improvements_analyzer.analyze(
                preprocessed_code['cleaned_code'],
                detected_language,
                structure_analysis,
                naming_analysis,
                quality_analysis
            )
            
            # Robustness: Add metadata about code completeness
            robustness_info = {
                'has_functions': len(structure_analysis.get('functions', [])) > 0,
                'has_classes': len(structure_analysis.get('classes', [])) > 0,
                'has_problem_statement': bool(problem_statement),
                'is_complete': True,  # Assume complete unless issues found
                'messages': []
            }
            
            # Add helpful messages for incomplete code
            if not robustness_info['has_functions'] and not robustness_info['has_classes']:
                robustness_info['messages'].append(
                    "No functions or classes detected — analysis limited to variable naming and code structure."
                )
            
            if not robustness_info['has_problem_statement']:
                robustness_info['messages'].append(
                    "No problem statement provided — naming suggestions will be generic. Add a problem statement for context-aware suggestions."
                )
            
            
            # Step 10: Auto-Refine Code based on suggestions
            from analyzers.python.code_refiner import CodeRefiner
            from analyzers.python.security_analyzer import SecurityAnalyzer
            from analyzers.python.performance_analyzer import PerformanceAnalyzer
            
            code_refiner = CodeRefiner()
            sec_analyzer = SecurityAnalyzer()
            perf_analyzer = PerformanceAnalyzer()
            
            refined_code = code_refiner.refine(
                code=code,
                language=detected_language,
                naming_analysis=naming_analysis,
                structure_analysis=structure_analysis
            )
            security_analysis = sec_analyzer.analyze(code, detected_language)
            performance_analysis = perf_analyzer.analyze(code, detected_language)
            
            # Compile comprehensive analysis results
            analysis_results = {
                'success': True,
                'language': detected_language,
                'preprocessed_code': preprocessed_code,
                'intent_analysis': intent_analysis,
                'structure_analysis': structure_analysis,
                'consistency_analysis': consistency_analysis,
                'quality_analysis': quality_analysis,
                'naming_analysis': naming_analysis,
                'improvements_analysis': improvements_analysis,
                'robustness_info': robustness_info,
                'refined_code': refined_code,
                'security_analysis': security_analysis,
                'performance_analysis': performance_analysis
            }
            
            # Absolute override to guarantee LOC exactly matches the physical editor lines
            # regardless of what radon or any backend preprocessing calculates.
            exact_editor_lines = code.count('\n') + 1
            if 'quality_analysis' in analysis_results and 'metrics' in analysis_results['quality_analysis']:
                if 'raw_metrics' in analysis_results['quality_analysis']['metrics']:
                    analysis_results['quality_analysis']['metrics']['raw_metrics']['loc'] = exact_editor_lines
            
            return jsonify(analysis_results)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An unexpected error occurred: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'CodeRefine'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
