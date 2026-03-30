// ===== DOM Elements =====
const fileInput = document.getElementById('fileInput');
const codeInput = document.getElementById('codeInput');
const clearBtn = document.getElementById('clearBtn');
const codeForm = document.getElementById('codeForm');
const errorDisplay = document.getElementById('errorDisplay');
const analyzeBtn = document.getElementById('analyzeBtn');

const loadingSection = document.getElementById('loadingSection');
const emptyState = document.getElementById('emptyState');
const resultsContainer = document.getElementById('resultsContainer');
const loadingText = document.getElementById('loadingText');

const langBtns = document.querySelectorAll('.lang-btn');
const languageSelect = document.getElementById('languageSelect');
const analyzingText = document.getElementById('analyzingText');

function setLanguage(lang) {
    if (languageSelect) languageSelect.value = lang;
    
    langBtns.forEach(btn => {
        if (btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
            btn.style.background = 'white';
            btn.style.color = '#0f172a';
            btn.style.fontWeight = '600';
            btn.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'transparent';
            btn.style.color = '#64748b';
            btn.style.fontWeight = '500';
            btn.style.boxShadow = 'none';
        }
    });

    if (analyzingText) {
        analyzingText.textContent = `Analyzing: ${lang.charAt(0).toUpperCase() + lang.slice(1)}`;
    }
    
    if (window.monaco && window.myEditor) {
        monaco.editor.setModelLanguage(window.myEditor.getModel(), lang === 'python' ? 'python' : 'java');
    }
}

langBtns.forEach(btn => {
    btn.addEventListener('click', () => setLanguage(btn.getAttribute('data-lang')));
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

function handleFileUpload(file) {
    const validExtensions = ['py', 'java', 'txt'];
    const extension = file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(extension)) {
        showError('Invalid file type. Please upload a .py, .java, or .txt file.');
        return;
    }

    if (file.size === 0) {
        showError('The uploaded file is empty.');
        return;
    }

    if (extension === 'py') setLanguage('python');
    if (extension === 'java') setLanguage('java');

    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result;
        if (!content.trim()) {
            showError('The uploaded file contains no readable text.');
            return;
        }
        if (window.myEditor) {
            window.myEditor.setValue(content);
        } else {
            codeInput.value = content;
        }
        hideError();
    };
    reader.readAsText(file);
}

window.myEditor = null;
require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.36.1/min/vs' }});
require(['vs/editor/editor.main'], function () {
    window.myEditor = monaco.editor.create(document.getElementById('editor'), {
        value: '',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', 'Courier New', monospace"
    });
    
    window.refinedEditorInstance = monaco.editor.create(document.getElementById('refinedEditor'), {
        value: '# Your refined code answers will appear here',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        readOnly: true,
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', 'Courier New', monospace"
    });
    
    window.myEditor.onDidChangeModelContent(() => {
        const val = window.myEditor.getValue();
        codeInput.value = val;
        
        const placeholder = document.getElementById('editorPlaceholder');
        if (placeholder) {
            placeholder.style.display = val ? 'none' : 'block';
        }
    });
    
    codeInput.value = window.myEditor.getValue();
});

clearBtn.addEventListener('click', () => {
    if (window.myEditor) window.myEditor.setValue('');
    else codeInput.value = '';
    fileInput.value = '';
    hideError();
});

codeForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const code = codeInput.value.trim();
    const problemStatement = document.getElementById('problemStatement').value.trim();

    if (!code) {
        showError('Please provide some code to analyze');
        return;
    }

    const formData = new FormData();
    formData.append('code', code);
    
    const language = document.getElementById('languageSelect')?.value || 'python';
    formData.append('language', language);
    
    if (problemStatement) {
        formData.append('problem_statement', problemStatement);
    }

    showLoading();

    try {
        
        updateLoadingText('Validating syntax...');
        await sleep(800);

        updateLoadingText('Preprocessing and normalizing code...');
        await sleep(600);

        updateLoadingText('Analyzing code structure and flow...');
        await sleep(700);

        updateLoadingText('Evaluating code quality metrics...');
        await sleep(600);

        updateLoadingText('Assessing naming and readability...');

        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Analysis failed');
        }

        displayResults(data);

    } catch (error) {
        hideLoading();
        showError(error.message || 'An error occurred during analysis');
    }
});

function showError(message) {
    errorDisplay.textContent = message;
    errorDisplay.style.display = 'block';
    errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    errorDisplay.style.display = 'none';
}

function showLoading() {
    emptyState.style.display = 'none';
    loadingSection.style.display = 'block';
    resultsContainer.style.display = 'none';
    hideError();
}

function hideLoading() {
    loadingSection.style.display = 'none';
}

function updateLoadingText(text) {
    loadingText.textContent = text;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function displayResults(data) {
    hideLoading();
    emptyState.style.display = 'none';
    resultsContainer.style.display = 'flex'; // Restoring flex display
    
    if (window.refinedEditorInstance && data.refined_code) {
        window.refinedEditorInstance.setValue(data.refined_code);
    }

    displayRobustnessInfo(data.robustness_info);

    displayOverview(data);

    displayQualityMetrics(data.quality_analysis);
    displayIssues(data);
    displayNamingAnalysis(data.naming_analysis);

    displayImprovements(data.improvements_analysis);
    
    if(data.security_analysis) {
        displaySecurityAnalysis(data.security_analysis);
    }
    
    displayDocumentation(data.structure_analysis);

    initCollapsibleSections();
}

function displayOverview(data) {
    const rawMetrics = data.quality_analysis.metrics.raw_metrics || {};
    const totalFunctions = data.structure_analysis.functions?.length || 0;
    const classesCount = data.structure_analysis.classes?.length || 0;

    let methodsCount = 0;
    data.structure_analysis.classes?.forEach(cls => {
        methodsCount += cls.methods?.length || 0;
    });

    const standalone = totalFunctions - methodsCount;

    document.getElementById('linesOfCode').textContent =
        rawMetrics.loc || rawMetrics.total_lines || 0;

    const funcElement = document.getElementById('functionsCount');
    funcElement.textContent = totalFunctions;

    const complexity = (data.performance_analysis && data.performance_analysis.complexity) ? data.performance_analysis.complexity : "-";
    const compElement = document.getElementById('timeComplexity');
    const compBadge = document.getElementById('complexityBadge');
    
    if (compElement && compBadge) {
        compElement.textContent = complexity;
        
        let color = '#a855f7'; 
        if (complexity.includes('O(1)') || complexity.includes('O(log')) color = '#10b981'; // Green (Excellent)
        else if (complexity.includes('O(N)') && !complexity.includes('N^')) color = '#f59e0b'; // Yellow (Average)
        else if (complexity.includes('N^') || complexity.includes('2^N')) color = '#ef4444'; // Red (Poor)
        
        compElement.style.color = color;
        compBadge.style.background = `${color}15`; 
        compBadge.style.borderColor = `${color}30`; 
    }
    if (methodsCount > 0 && standalone > 0) {
        funcElement.title = `Total: ${totalFunctions} callable functions\n(${standalone} standalone + ${methodsCount} in classes)`;
    } else if (totalFunctions > 0) {
        funcElement.title = `${totalFunctions} total function(s)`;
    }

    document.getElementById('classesCount').textContent = classesCount;
}

function displayQualityMetrics(qualityAnalysis) {
    const container = document.getElementById('qualityMetrics');

    // Debug logging
    console.log('📊 Quality Analysis Data:', qualityAnalysis);
    console.log('📈 Metrics:', qualityAnalysis?.metrics);

    const metrics = qualityAnalysis.metrics;

    let html = '<div class="metrics-grid">';

    if (metrics.raw_metrics) {
        const raw = metrics.raw_metrics;

        if (raw.loc !== undefined) {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Total Lines</div>
                    <div class="metric-value">${raw.loc}</div>
                </div>
            `;
        }

        if (raw.sloc !== undefined) {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Source Lines</div>
                    <div class="metric-value">${raw.sloc}</div>
                </div>
            `;
        }

        if (raw.comments !== undefined) {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Comment Lines</div>
                    <div class="metric-value">${raw.comments}</div>
                </div>
            `;
        }

        if (raw.blank !== undefined) {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Blank Lines</div>
                    <div class="metric-value">${raw.blank}</div>
                </div>
            `;
        }
    }

    if (metrics.maintainability_index !== null && metrics.maintainability_index !== undefined) {
        const mi = metrics.maintainability_index;
        const miColor = mi >= 80 ? '#28a745' : mi >= 60 ? '#ffc107' : '#dc3545';
        console.log(`🔍 Maintainability Index: ${mi} (color: ${miColor})`);
        html += `
            <div class="metric-card">
                <div class="metric-label">Maintainability Index</div>
                <div class="metric-value" style="color: ${miColor}">${mi}</div>
            </div>
        `;
    } else {
        console.warn('⚠️ Maintainability Index is null or undefined!');
    }

    html += '</div>';

    if (metrics.complexity && metrics.complexity.length > 0) {
        console.log(`🔢 Complexity data:`, metrics.complexity);
        html += '<h4 style="margin-top: 24px; margin-bottom: 16px; color: var(--text-secondary);">Cyclomatic Complexity:</h4>';
        html += '<div class="complexity-list">';

        metrics.complexity.forEach(item => {
            html += `
                <div class="complexity-item">
                    <span class="complexity-name">${escapeHtml(item.name)}</span>
                    <div>
                        <span style="margin-right: 12px; color: var(--text-secondary);">${item.complexity}</span>
                        <span class="complexity-badge ${item.rank}">${item.rank}</span>
                    </div>
                </div>
            `;
        });

        html += '</div>';
    } else {
        console.warn('⚠️ No complexity data found!');
    }

    container.innerHTML = html;
}

function displayIssues(data) {
    const issuesCard = document.getElementById('issuesCard');
    const container = document.getElementById('detectedIssues');

    const codeQualityIssues = [];

    if (data.consistency_analysis && data.consistency_analysis.issues) {
        codeQualityIssues.push(...data.consistency_analysis.issues);
    }

    if (data.quality_analysis && data.quality_analysis.code_smells) {
        codeQualityIssues.push(...data.quality_analysis.code_smells);
    }
    if (codeQualityIssues.length === 0) {
        if (issuesCard) issuesCard.style.display = 'none';
        return;
    }

    if (issuesCard) issuesCard.style.display = 'block';

    let html = '';

    const renderIssueGroup = (title, icon, issues) => {
        if (issues.length === 0) return '';
        
        const groupedIssues = {};
        issues.forEach(issue => {
            const type = issue.type || 'issue';
            if (!groupedIssues[type]) groupedIssues[type] = [];
            groupedIssues[type].push(issue);
        });

        const types = Object.keys(groupedIssues);

        let groupHtml = `
            <div style="margin-bottom: 24px;">
                <h4 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
                    ${icon} ${title}
                </h4>
        `;

        if (types.length > 0) {
            groupHtml += `<div class="issue-tabs" style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;" onclick="
                if(event.target.closest('.issue-tab-btn')) {
                    const btn = event.target.closest('.issue-tab-btn');
                    const type = btn.getAttribute('data-type');
                    const container = btn.closest('.issue-tabs').nextElementSibling;
                    
                    btn.closest('.issue-tabs').querySelectorAll('.issue-tab-btn').forEach(b => {
                        b.style.background = 'var(--bg-tertiary)';
                        b.style.color = 'var(--text-primary)';
                        if(b.querySelector('.badge')) b.querySelector('.badge').style.background = 'var(--bg-secondary)';
                    });
                    btn.style.background = '#a855f7';
                    btn.style.color = '#fff';
                    if(btn.querySelector('.badge')) btn.querySelector('.badge').style.background = 'rgba(255,255,255,0.2)';
                    
                    container.querySelectorAll('.issue-type-group').forEach(list => {
                        list.style.display = list.getAttribute('data-type') === type ? 'block' : 'none';
                    });
                }
            ">`;
            types.forEach((type, index) => {
                const isActive = index === 0;
                const displayType = type.replace(/_/g, ' ');
                const bg = isActive ? '#a855f7' : 'var(--bg-tertiary)';
                const color = isActive ? '#fff' : 'var(--text-primary)';
                const badgeBg = isActive ? 'rgba(255,255,255,0.2)' : 'var(--bg-secondary)';
                
                groupHtml += `
                    <button type="button" class="issue-tab-btn" data-type="${type}" style="padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-color); background: ${bg}; color: ${color}; transition: all 0.2s; display: flex; align-items: center; gap: 6px;">
                        <span style="text-transform: capitalize;">${displayType}</span>
                        <span class="badge" style="background: ${badgeBg}; padding: 2px 6px; border-radius: 12px; font-size: 11px;">${groupedIssues[type].length}</span>
                    </button>
                `;
            });
            groupHtml += `</div>`;
        }

        groupHtml += `<div class="issues-content-container">`;

        types.forEach((type, index) => {
            const isVisible = index === 0 ? 'block' : 'none';
            groupHtml += `<ul class="issues-list issue-type-group" data-type="${type}" style="margin-top: 0; display: ${isVisible}; list-style: none; padding: 0;">`;
            
            groupedIssues[type].forEach(issue => {
                const rawDesc = issue.description || issue.message || 'Issue detected';
                const location = issue.location || (issue.line ? `Line ${issue.line}` : '');
                
                let formattedDesc = escapeHtml(rawDesc);
                if (formattedDesc.includes('Problem:') && formattedDesc.includes('Suggestion:')) {
                    const parts = formattedDesc.split('Suggestion:');
                    formattedDesc = `
                        <div style="margin-bottom: 8px;">
                            <strong style="color: #ef4444; display: block; margin-bottom: 2px;">Problem:</strong> 
                            <span style="color: var(--text-primary);">${parts[0].replace('Problem:', '').trim()}</span>
                        </div>
                        <div style="background: var(--bg-tertiary); padding: 10px; border-radius: 6px; border-left: 3px solid #3b82f6; border-top: 1px solid var(--border-color); border-right: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);">
                            <strong style="color: #3b82f6; display: flex; align-items: center; gap: 4px; margin-bottom: 2px;">
                                💡 Suggestion:
                            </strong> 
                            <span style="color: var(--text-secondary);">${parts[1].trim()}</span>
                        </div>
                    `;
                } else {
                    formattedDesc = formattedDesc.replace(/\n/g, '<br>');
                }

                groupHtml += `
                    <li class="issue-item" style="border-left: 4px solid #ef4444; background: var(--bg-secondary); border-radius: 6px; padding: 16px; margin-bottom: 12px; border-top: 1px solid var(--border-color); border-right: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);">
                        <div class="issue-description" style="margin-bottom: 12px; line-height: 1.5; color: var(--text-secondary);">${formattedDesc}</div>
                        ${location ? `<div class="issue-location" style="font-family: monospace; font-size: 13px; color: var(--text-muted); background: var(--bg-tertiary); padding: 4px 8px; border-radius: 4px; display: inline-block; border: 1px solid var(--border-color);">📌 ${escapeHtml(location)}</div>` : ''}
                    </li>
                `;
            });
            groupHtml += `</ul>`;
        });
        
        groupHtml += '</div></div>';
        return groupHtml;
    };

    html += renderIssueGroup('🔴 Code Quality Issues', '', codeQualityIssues);

    container.innerHTML = html;
}


function initCollapsibleInputs() {
    const inputHeaders = document.querySelectorAll('.collapsible-input-header');

    inputHeaders.forEach(header => {
        header.addEventListener('click', function () {
            const targetId = this.getAttribute('data-target');
            const body = document.getElementById(targetId);

            if (body) {
                this.classList.toggle('collapsed');
                body.classList.toggle('collapsed');
            }
        });
    });
}


function displayDocumentation(structureAnalysis) {
    const container = document.getElementById('fullDocContent');
    if (!container) return;
    
    window.currentDocData = structureAnalysis;
    
    const functions = structureAnalysis.functions || [];
    const classes = structureAnalysis.classes || [];
    
    if (functions.length === 0 && classes.length === 0) {
        document.getElementById('viewDocsBtn').style.display = 'none';
        return;
    }
    
    document.getElementById('viewDocsBtn').style.display = 'flex';
    
    let allIssues = [];
    classes.forEach(c => {
        if (c.warnings) {
            c.warnings.forEach(w => allIssues.push({...w, location: `Class: ${c.name}`}));
        }
        (c.methods || []).forEach(m => {
            if (m.warnings) {
                m.warnings.forEach(w => allIssues.push({...w, location: `Method: ${c.name}.${m.name}`}));
            }
        });
    });
    functions.forEach(f => {
        if (f.warnings) {
            f.warnings.forEach(w => allIssues.push({...w, location: `Function: ${f.name}`}));
        }
    });

    let totalWarnings = allIssues.length;
    let quality = "Excellent";
    let qColor = "#10b981"; // green
    if (totalWarnings > 5) { quality = "Poor"; qColor = "#ef4444"; } // red
    else if (totalWarnings > 0) { quality = "Moderate"; qColor = "#f59e0b"; } // yellow
    
    let html = `
    <style>
        .method-card:hover { border-color: rgba(59, 130, 246, 0.5); transform: translateX(4px); background: var(--bg-secondary); }
        #fullDocContent { max-width: 100%; color: var(--text-primary); }
        .section-header { font-size: 32px; font-weight: 800; color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 16px; margin-bottom: 32px; display: flex; align-items: center; gap: 16px; letter-spacing: -0.5px; }
        .issue-card { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: var(--shadow-md); transition: transform 0.2s; }
        .issue-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
        .issue-card.red-border { border-left: 5px solid #ef4444; }
        .issue-card.yellow-border { border-left: 5px solid #f59e0b; }
        .issue-card-title { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
        .issue-loc { display: inline-block; background: var(--bg-tertiary); color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; font-size: 14px; padding: 4px 10px; border-radius: 6px; margin-bottom: 16px; border: 1px solid var(--border-color); }
        .issue-grid { display: flex; flex-direction: column; gap: 12px; font-size: 15px; }
        .issue-row { display: grid; grid-template-columns: 60px 1fr; gap: 12px; align-items: start; background: var(--bg-secondary); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color); }
        
        /* High Contrast Light Colors */
        .text-primary { color: var(--text-primary); }        
        .text-secondary { color: var(--text-secondary); }
        .text-accent { color: #2563eb; } 
        .text-success { color: #10b981; }
        .text-warning { color: #d97706; }
        .text-danger { color: #dc2626; }
        .text-label { color: var(--text-secondary); font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 1px; }

        @media print {
            body * { visibility: hidden; }
            #documentationOverlay, #documentationOverlay * { visibility: visible; }
            #documentationOverlay { position: absolute; left: 0; top: 0; background: var(--bg-primary); color: var(--text-primary); }
            .issue-card { border: 1px solid #ccc; box-shadow: none; break-inside: avoid; }
            .method-card { break-inside: avoid; border: 1px solid #ccc; }
        }
    </style>
    
    <!-- ========================================== -->
    <!-- SECTION A: HANDOVER DOCUMENTATION FORMAT   -->
    <!-- ========================================== -->
    <div id="printDocsSection" style="display: block;">
        
        <!-- Document-specific Summary -->
        <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px 32px; margin-bottom: 32px; display: flex; gap: 40px; align-items: center;">
            <div style="display: flex; flex-direction: column;">
                <span class="text-label" style="margin-bottom: 4px;">Total Classes</span>
                <span style="font-size: 28px; font-weight: 800; color: var(--text-primary); font-family: 'JetBrains Mono', monospace;">${classes.length}</span>
            </div>
            <div style="display: flex; flex-direction: column;">
                <span class="text-label" style="margin-bottom: 4px;">Total Functions</span>
                <span style="font-size: 28px; font-weight: 800; color: var(--text-primary); font-family: 'JetBrains Mono', monospace;">${functions.length}</span>
            </div>
        </div>

        <div style="background: var(--bg-secondary); border-left: 4px solid #3b82f6; padding: 16px 24px; border-radius: 8px; margin-bottom: 32px;">
            <p style="color: var(--text-primary); font-size: 16px; line-height: 1.5; margin: 0;">
                <strong>Handover Documentation:</strong> Official reference for developers. This outlines the purpose, parameters, and returns of the logic. Architectural issues are explicitly excluded from this view.
            </p>
        </div>
    `;
    
    if (classes.length > 0) {
        html += '<h3 style="font-size: 24px; font-weight: 700; margin-bottom: 24px; color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 12px; display: flex; align-items: center; gap: 12px;"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:#3b82f6"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg> Classes Layout</h3>';
        html += '<div style="display: flex; flex-direction: column; gap: 40px; margin-bottom: 56px;">';
        
        classes.forEach(cls => {
            const methodsHtml = (cls.methods || []).map(method => {
                const params = method.params && method.params.length > 0 ? escapeHtml(method.params.join(', ')) : 'None';
                const returns = (method.returns && method.returns.length > 0 && method.returns[0] !== 'Unknown') 
                    ? escapeHtml(method.returns.join(' | ')) 
                    : 'Void/Self';
                const desc = method.docstring ? escapeHtml(method.docstring) : 'No description provided.';
                
                return `
                    <div class="method-card" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; transition: all 0.2s ease;">
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 18px; margin-bottom: 20px; color: var(--text-primary); border-bottom: 1px solid var(--bg-tertiary); padding-bottom: 12px;">
                            <span style="color: #2563eb; font-weight: 700;">${escapeHtml(method.name)}()</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 100px 1fr; gap: 16px; font-size: 15px;">
                            <span class="text-label" style="margin-top:2px;">Purpose:</span>
                            <span style="color: var(--text-secondary); line-height: 1.6; font-size: 16px;">${desc}</span>
                            
                            <span class="text-label" style="margin-top:2px;">Params:</span>
                            <span style="color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; background: var(--bg-tertiary); padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content;">${params}</span>
                            
                            <span class="text-label" style="margin-top:2px;">Returns:</span>
                            <span style="color: #6ee7b7; font-weight: 600; font-size: 16px;">${returns}</span>
                        </div>
                    </div>
                `;
            }).join('<div style="height:20px;"></div>');
            
            html += `
                <div class="doc-hover-card" style="background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-bottom: 24px;">
                    <div style="padding: 32px; border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                            <span style="background: #e0f2fe; color: #0284c7; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">Class</span>
                            <h3 style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 0; font-family: 'JetBrains Mono', monospace;">${escapeHtml(cls.name)}</h3>
                        </div>
                        <div style="display: grid; grid-template-columns: 100px 1fr; gap: 16px; font-size: 16px; background: var(--bg-primary); padding: 20px; border-radius: 12px; border: 1px solid var(--border-color);">
                            <span class="text-label" style="margin-top:2px;">Purpose:</span>
                            <span style="color: var(--text-secondary); line-height: 1.6;">${escapeHtml(cls.docstring || 'No purpose documented.')}</span>
                        </div>
                    </div>
                    ${cls.methods && cls.methods.length > 0 ? `
                        <div style="padding: 32px;">
                            <h4 style="font-size: 14px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-secondary); margin-bottom: 24px; font-weight: 700; display: flex; align-items: center; gap: 12px;">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                Methods
                            </h4>
                            <div>${methodsHtml}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    html += '</div>'; 
    html += `
        <div id="printAuditSection" style="display: none;">
            
            <!-- Code Review Specific Summary -->
            <div style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px 32px; margin-bottom: 32px; display: flex; gap: 40px; align-items: center; justify-content: space-between;">
                <div style="display: flex; gap: 40px;">
                    <div style="display: flex; flex-direction: column;">
                        <span class="text-label" style="margin-bottom: 4px;">Total Issues</span>
                        <span style="font-size: 28px; font-weight: 800; color: ${totalWarnings > 0 ? '#ef4444' : '#10b981'}; font-family: 'JetBrains Mono', monospace;">${totalWarnings}</span>
                    </div>
                    <div style="display: flex; flex-direction: column;">
                        <span class="text-label" style="margin-bottom: 4px;">Code Quality</span>
                        <span style="font-size: 28px; font-weight: 800; color: ${qColor}; text-transform: uppercase;">${quality}</span>
                    </div>
                </div>
            </div>

            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 16px 24px; border-radius: 8px; margin-bottom: 32px;">
                <p style="color: #fca5a5; font-size: 16px; line-height: 1.5; margin: 0;">
                    <strong>Code Review Report:</strong> Strict technical review outlining architectural debt, structural vulnerabilities, and readability improvements.
                </p>
            </div>
    `;

    if (allIssues.length === 0) {
        html += `
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 16px; padding: 60px 40px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);">
                <div style="font-size: 64px; margin-bottom: 24px;">🏆</div>
                <h3 style="color: #6ee7b7; font-size: 28px; font-weight: 800; margin-bottom: 12px;">Flawless Code!</h3>
                <p style="color: var(--text-secondary); font-size: 18px;">Zero structural issues, zero naming violations. Excellent quality.</p>
            </div>
        `;
    } 
    html += '</div>'; 
    
    container.innerHTML = html;
}

