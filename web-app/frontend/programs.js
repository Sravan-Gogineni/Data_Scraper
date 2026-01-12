document.addEventListener('DOMContentLoaded', () => {
    const universityNameInput = document.getElementById('universityName');
    const stepButtons = document.querySelectorAll('.step-btn');
    const logsContainer = document.getElementById('logs');
    const statusArea = document.getElementById('statusArea');
    const resultsContainer = document.getElementById('results');
    const fileList = document.getElementById('fileList');
    const statusBadge = document.getElementById('statusBadge');

    let isProcessing = false;

    stepButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const step = btn.dataset.step;
            runStep(step);
        });
    });

    async function runStep(step) {
        if (isProcessing) return;

        const universityName = universityNameInput.value.trim();
        if (!universityName) {
            shakeInput(universityNameInput);
            log('University Name is required.', 'error');
            return;
        }

        setLoading(true);
        setStatus(`Running Step ${step}`, 'initializing');
        log(`Starting Step ${step} for ${universityName}...`);

        const payload = {
            university_name: universityName,
            step: parseInt(step)
        };

        try {
            const startTime = Date.now();
            const response = await fetch('/api/extract/programs', {
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
                buffer = lines.pop(); 

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.status === 'progress') {
                             log(data.message, 'system');
                        } else if (data.status === 'warning') {
                             log(data.message, 'warning');
                        } else if (data.status === 'complete') {
                             const duration = ((Date.now() - startTime) / 1000).toFixed(1);
                             log(`Step ${step} completed in ${duration}s`, 'success');
                             setStatus('Success', 'success');
                             if (data.files && Object.keys(data.files).length > 0) {
                                showResults(data.files);
                             }
                             setLoading(false);
                             return;
                        } else if (data.error) {
                             throw new Error(data.error);
                        } else if (data.status === 'error') {
                             throw new Error(data.message);
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
    }

    function setLoading(isLoading) {
        isProcessing = isLoading;
        stepButtons.forEach(btn => btn.disabled = isLoading);
        
        if (isLoading) {
            statusArea.classList.remove('hidden');
            resultsContainer.classList.add('hidden'); // Hide previous results while running new step
            // We don't clear logs here to keep history, or maybe we should?
            // Let's clear for cleaner view
            logsContainer.innerHTML = ''; 
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }
    }

    function setStatus(text, type) {
        statusBadge.textContent = text;
        statusBadge.className = 'badge ' + type;
    }

    function log(message, type = 'system') {
        const div = document.createElement('div');
        div.className = `log-line ${type}`;
        div.textContent = `> ${message}`;
        logsContainer.appendChild(div);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    function showResults(files) {
        resultsContainer.classList.remove('hidden');
        fileList.innerHTML = ''; 

        const fileTypes = {
            'csv': { icon: '📊', label: 'CSV Data' },
            'excel': { icon: '📗', label: 'Excel Report' },
            'json': { icon: '📦', label: 'JSON Data' }
        };

        for (const [key, path] of Object.entries(files)) {
            // key might contain hints like "grad_csv"
            let typeKey = 'json';
            if (key.includes('csv')) typeKey = 'csv';
            else if (key.includes('xlsx')) typeKey = 'excel';

            const meta = fileTypes[typeKey] || { icon: '📄', label: key.toUpperCase() };
            const filename = path.split('/').pop(); // path is /api/download/filename

            const link = document.createElement('a');
            link.href = path; 
            link.download = filename;
            link.className = 'file-item';
            link.style.textDecoration = 'none';

            link.innerHTML = `
                <span class="file-icon">${meta.icon}</span>
                <div class="file-info">
                    <div style="font-size:0.75rem; color: #94a3b8;">${meta.label}</div>
                    <div class="file-name" title="${filename}">${filename}</div>
                </div>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: auto; color: var(--primary);"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            `;
            fileList.appendChild(link);
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
            element.style.borderColor = 'rgba(255, 255, 255, 0.1)';
        }, 2000);
    }
});
