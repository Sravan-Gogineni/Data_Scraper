document.addEventListener('DOMContentLoaded', () => {
    const extractBtn = document.getElementById('extractBtn');
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

    // --- Helper Functions ---

    function setLoading(isLoading) {
        extractBtn.disabled = isLoading;
        const loader = extractBtn.querySelector('.btn-loader');
        const text = extractBtn.querySelector('.btn-text');
        
        if (isLoading) {
            loader.classList.remove('hidden');
            text.textContent = 'Processing...';
            document.getElementById('statusArea').classList.remove('hidden');
            document.getElementById('results').classList.add('hidden');
            document.getElementById('logs').innerHTML = ''; // Clear old logs
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        } else {
            loader.classList.add('hidden');
            text.textContent = 'Extract Data';
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

    function showResults(files) {
        const container = document.getElementById('results');
        const list = document.getElementById('fileList');
        
        container.classList.remove('hidden');
        list.innerHTML = ''; // Clear

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
