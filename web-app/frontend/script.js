document.addEventListener('DOMContentLoaded', () => {
    const extractBtn = document.getElementById('extractBtn');
    const fullExtractBtn = document.getElementById('fullExtractBtn');
    const universityNameInput = document.getElementById('universityName');

    // URL Inputs
    const commonAidUrl = document.getElementById('commonAidUrl');
    const ugAidUrl = document.getElementById('ugAidUrl');
    const gradAidUrl = document.getElementById('gradAidUrl');

    extractBtn.addEventListener('click', async () => {
        const universityName = universityNameInput.value.trim();

        // Basic Validation
        if (!universityName) {
            shakeInput(universityNameInput);
            log('University Name is required.', 'error');
            return;
        }

        // Prepare Payload
        const payload = {
            university_name: universityName,
            common_financial_aid_urls: commonAidUrl.value.trim() || null,
            undergraduate_financial_aid_urls: ugAidUrl.value.trim() || null,
            graduate_financial_aid_urls: gradAidUrl.value.trim() || null
        };

        // UI State: Processing
        setLoading(true);
        setStatus('Processing', 'initializing');
        log(`Starting extraction for ${universityName}...`);

        try {
            const startTime = Date.now();

            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Server error');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep incomplete chunk

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));

                        if (data.status === 'progress') {
                            log(data.message, 'system');
                        } else if (data.status === 'complete') {
                            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
                            log(`Extraction completed in ${duration}s`, 'success');
                            setStatus('Success', 'success');
                            showResults(data.files);
                            setLoading(false);
                            return;
                        } else if (data.error) {
                            throw new Error(data.error);
                        }
                    }
                }
            }

        } catch (error) {
            console.error(error);
            log(`Error: ${error.message}`, 'error');
            setStatus('Failed', 'error');
            setLoading(false);
        }
    });

    // Full Extraction Logic
    if (fullExtractBtn) {
        fullExtractBtn.addEventListener('click', async () => {
            const universityName = universityNameInput.value.trim();

            if (!universityName) {
                shakeInput(universityNameInput);
                log('University Name is required.', 'error');
                return;
            }

            // Prepare Payload for Institution
            const instPayload = {
                university_name: universityName,
                common_financial_aid_urls: commonAidUrl.value.trim() || null,
                undergraduate_financial_aid_urls: ugAidUrl.value.trim() || null,
                graduate_financial_aid_urls: gradAidUrl.value.trim() || null
            };

            setLoading(true, true); // true for isLoading, true for isFullExtraction
            setStatus('Starting Full Extraction', 'initializing');
            log(`Starting FULL extraction for ${universityName}...`);

            try {
                const startTime = Date.now();

                // 1. Institution Extraction
                log('--- Step 1: Institution Extraction ---', 'system');
                await runExtraction('/api/extract', instPayload, 'Institution');

                // 2. Department Extraction
                log('--- Step 2: Department Extraction ---', 'system');
                const deptPayload = { university_name: universityName };
                let departmentsFound = false;

                while (!departmentsFound) {
                    try {
                        const result = await runExtraction('/api/extract/department', deptPayload, 'Department');
                        // Check if we actually found files/departments
                        // The backend stream returns a final JSON with "files". 
                        // If that JSON has files, we assume success. 
                        // If it was empty or error, runExtraction would likely throw or we need to check result.
                        // For now, assuming runExtraction returns the final complete data object if successful.

                        if (result && result.files && Object.keys(result.files).length > 0) {
                            departmentsFound = true;
                            log('Departments found and extracted.', 'success');
                        } else {
                            log('No departments found. Retrying in 5 seconds...', 'warning');
                            await new Promise(r => setTimeout(r, 5000));
                        }
                    } catch (e) {
                        log(`Department extraction failed: ${e.message}. Retrying in 5 seconds...`, 'warning');
                        await new Promise(r => setTimeout(r, 5000));
                    }
                }

                // 3. Programs Extraction
                log('--- Step 3: Programs Extraction (Full Automation) ---', 'system');
                const progPayload = {
                    university_name: universityName,
                    step: 9 // Full Automation
                };
                await runExtraction('/api/extract/programs', progPayload, 'Programs');

                const duration = ((Date.now() - startTime) / 1000).toFixed(1);
                log(`FULL EXTRACTION COMPLETED in ${duration}s`, 'success');
                setStatus('Full Extraction Complete', 'success');
                setLoading(false);

            } catch (error) {
                console.error(error);
                log(`Critical Error: ${error.message}`, 'error');
                setStatus('Failed', 'error');
                setLoading(false);
            }
        });
    }

    // Generic Extraction Runner for consistency
    async function runExtraction(url, payload, label) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.error || 'Server error');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalData = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));

                    if (data.status === 'progress') {
                        log(`[${label}] ${data.message}`, 'system');
                    } else if (data.status === 'complete') {
                        log(`[${label}] Complete`, 'success');
                        showResults(data.files, /* append */ true);
                        finalData = data;
                    } else if (data.error) {
                        throw new Error(data.error);
                    }
                }
            }
        }
        return finalData;
    }

    // --- Helper Functions ---

    function setLoading(isLoading, isFull = false) {
        extractBtn.disabled = isLoading;
        if (fullExtractBtn) fullExtractBtn.disabled = isLoading;

        const loader = isFull && fullExtractBtn ? fullExtractBtn.querySelector('.btn-loader') : extractBtn.querySelector('.btn-loader');
        const text = isFull && fullExtractBtn ? fullExtractBtn.querySelector('.btn-text') : extractBtn.querySelector('.btn-text');

        if (isLoading) {
            if (loader) loader.classList.remove('hidden');
            if (text) text.textContent = 'Processing...';
            document.getElementById('statusArea').classList.remove('hidden');
            document.getElementById('results').classList.add('hidden');
            document.getElementById('logs').innerHTML = ''; // Clear old logs
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        } else {
            // Reset both just in case
            extractBtn.querySelector('.btn-loader').classList.add('hidden');
            extractBtn.querySelector('.btn-text').textContent = 'Extract Data';
            if (fullExtractBtn) {
                fullExtractBtn.querySelector('.btn-loader').classList.add('hidden');
                fullExtractBtn.querySelector('.btn-text').textContent = 'Full Extraction';
            }
        }
    }

    function setStatus(text, type) {
        const badge = document.getElementById('statusBadge');
        badge.textContent = text;
        badge.className = 'badge ' + type;
    }

    function log(message, type = 'system') {
        const logs = document.getElementById('logs');
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = `> ${message}`;
        logs.appendChild(div);
        logs.scrollTop = logs.scrollHeight;
    }

    function showResults(files, append = false) {
        const container = document.getElementById('results');
        const list = document.getElementById('fileList');

        container.classList.remove('hidden');
        if (!append) list.innerHTML = ''; // Clear only if not appending

        const fileTypes = {
            'csv': { icon: '📊', label: 'CSV Data' },
            'excel': { icon: '📗', label: 'Excel Report' },
            'json': { icon: '📦', label: 'JSON Data' }
        };

        for (const [key, path] of Object.entries(files)) {
            const meta = fileTypes[key] || { icon: '📄', label: key.toUpperCase() };
            const filename = path.split(/[/\\]/).pop();

            // Create anchor tag for download
            const link = document.createElement('a');
            link.href = path; // The backend now returns the specific API download path
            link.download = filename; // Suggest filename
            link.className = 'file-item';
            link.style.textDecoration = 'none'; // Ensure no underline

            link.innerHTML = `
                <span class="file-icon">${meta.icon}</span>
                <div class="file-info">
                    <div style="font-size:0.75rem; color: #94a3b8;">${meta.label}</div>
                    <div class="file-name" title="${filename}">${filename}</div>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto; color: var(--primary);"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            `;
            list.appendChild(link);
        }
    }

    function shakeInput(element) {
        element.style.borderColor = 'var(--error)';
        element.animate([
            { transform: 'translateX(0)' },
            { transform: 'translateX(-10px)' },
            { transform: 'translateX(10px)' },
            { transform: 'translateX(0)' }
        ], { duration: 300 });

        setTimeout(() => {
            element.style.borderColor = 'var(--surface-border)';
        }, 2000);
    }
});
