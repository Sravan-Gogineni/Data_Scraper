document.addEventListener('DOMContentLoaded', () => {
    // --- Mode Toggle ---
    const modeSingleBtn = document.getElementById('modeSingle');
    const modeBatchBtn = document.getElementById('modeBatch');
    const singleMode = document.getElementById('singleMode');
    const batchMode = document.getElementById('batchMode');

    modeSingleBtn.addEventListener('click', () => switchMode('single'));
    modeBatchBtn.addEventListener('click', () => switchMode('batch'));

    function switchMode(mode) {
        if (mode === 'single') {
            modeSingleBtn.classList.add('active');
            modeBatchBtn.classList.remove('active');
            singleMode.classList.remove('hidden');
            batchMode.classList.add('hidden');
        } else {
            modeBatchBtn.classList.add('active');
            modeSingleBtn.classList.remove('active');
            batchMode.classList.remove('hidden');
            singleMode.classList.add('hidden');
        }
        resetStatusArea();
    }

    // --- File Drop Area ---
    const fileDropArea = document.getElementById('fileDropArea');
    const batchFileInput = document.getElementById('batchFile');
    const fileChosenEl = document.getElementById('fileChosen');
    const fileDropLabel = document.getElementById('fileDropLabel');

    fileDropArea.addEventListener('click', () => batchFileInput.click());

    fileDropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropArea.classList.add('drag-over');
    });

    fileDropArea.addEventListener('dragleave', () => fileDropArea.classList.remove('drag-over'));

    fileDropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropArea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file) setChosenFile(file);
    });

    batchFileInput.addEventListener('change', () => {
        if (batchFileInput.files[0]) setChosenFile(batchFileInput.files[0]);
    });

    function setChosenFile(file) {
        fileChosenEl.textContent = `Selected: ${file.name}`;
        fileChosenEl.classList.remove('hidden');
        fileDropLabel.innerHTML = `Drag & drop or <span class="browse-link">browse</span>`;
        batchFileInput._selectedFile = file;
    }

    // --- Single University Extraction ---
    const extractBtn = document.getElementById('extractBtn');
    const universityNameInput = document.getElementById('universityName');

    extractBtn.addEventListener('click', async () => {
        const universityName = universityNameInput.value.trim();
        if (!universityName) {
            shakeInput(universityNameInput);
            log('University Name is required.', 'error');
            return;
        }

        resetStatusArea();
        document.getElementById('batchProgress').classList.add('hidden');
        setLoading(extractBtn, true, 'Processing...');
        setStatus('Starting Full Extraction', 'initializing');
        log(`Starting FULL extraction for ${universityName}...`);

        try {
            const startTime = Date.now();
            const response = await fetch('/api/extract/all', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ university_name: universityName })
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Server error');
            }

            await consumeStream(response, {
                onProgress: (data) => log(data.message, 'system'),
                onWarning: (data) => log(data.message, 'warning'),
                onComplete: (data, startTime) => {
                    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
                    log(`FULL EXTRACTION COMPLETED in ${duration}s`, 'success');
                    setStatus('Complete', 'success');
                    if (data.files && Object.keys(data.files).length > 0) showResults(data.files);
                    setLoading(extractBtn, false, 'Start Full Extraction');
                },
                onError: (msg) => { throw new Error(msg); },
                startTime: Date.now()
            });

        } catch (error) {
            console.error(error);
            log(`Error: ${error.message}`, 'error');
            setStatus('Failed', 'error');
            setLoading(extractBtn, false, 'Start Full Extraction');
        }
    });

    // --- Batch Extraction ---
    const batchExtractBtn = document.getElementById('batchExtractBtn');

    batchExtractBtn.addEventListener('click', async () => {
        const file = batchFileInput._selectedFile || batchFileInput.files[0];
        if (!file) {
            fileDropArea.style.borderColor = 'var(--error)';
            setTimeout(() => fileDropArea.style.borderColor = '', 2000);
            log('Please select a CSV or XLSX file.', 'error');
            return;
        }

        resetStatusArea();
        document.getElementById('batchProgress').classList.remove('hidden');
        setLoading(batchExtractBtn, true, 'Processing...');
        setStatus('Batch Starting', 'initializing');
        log(`Starting batch extraction from: ${file.name}...`);

        const formData = new FormData();
        formData.append('batch_file', file);

        try {
            const response = await fetch('/api/extract/batch', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const result = await response.json();
                throw new Error(result.error || 'Server error');
            }

            const startTime = Date.now();
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            // Track per-university state
            const universityItems = {};

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const data = JSON.parse(line.slice(6));

                    if (data.status === 'batch_start') {
                        log(data.message, 'system');
                        updateBatchProgress(0, data.total);
                        initBatchList(data.total);

                    } else if (data.status === 'university_start') {
                        log(`\u25b6 [${data.index}/${data.total}] ${data.university}`, 'system');
                        setUniversityStatus(data.index, data.university, 'running', universityItems);
                        updateBatchProgress(data.index - 1, data.total);

                    } else if (data.status === 'progress') {
                        log(data.message, 'system');

                    } else if (data.status === 'warning') {
                        log(data.message, 'warning');

                    } else if (data.status === 'university_complete') {
                        log(`\u2713 [${data.index}/${data.total}] Completed: ${data.university}`, 'success');
                        setUniversityStatus(data.index, data.university, 'done', universityItems);
                        updateBatchProgress(data.index, data.total);
                        if (data.files && Object.keys(data.files).length > 0) {
                            appendResults(data.university, data.files);
                        }

                    } else if (data.status === 'university_error') {
                        log(data.message, 'error');
                        setUniversityStatus(data.index, data.university, 'error', universityItems);
                        updateBatchProgress(data.index, data.total);

                    } else if (data.status === 'batch_complete') {
                        const duration = ((Date.now() - startTime) / 1000).toFixed(1);
                        log(`BATCH EXTRACTION COMPLETED in ${duration}s`, 'success');
                        setStatus('Complete', 'success');
                        updateBatchProgress(data.total, data.total);
                        setLoading(batchExtractBtn, false, 'Start Batch Extraction');
                        return;

                    } else if (data.error) {
                        throw new Error(data.error);
                    }
                }
            }

        } catch (error) {
            console.error(error);
            log(`Error: ${error.message}`, 'error');
            setStatus('Failed', 'error');
            setLoading(batchExtractBtn, false, 'Start Batch Extraction');
        }
    });

    // --- Batch UI Helpers ---

    function initBatchList(total) {
        const list = document.getElementById('batchUniversityList');
        list.innerHTML = '';
        for (let i = 1; i <= total; i++) {
            const item = document.createElement('div');
            item.className = 'batch-uni-item pending';
            item.id = `batch-uni-${i}`;
            item.innerHTML = `<span class="batch-uni-icon">○</span><span class="batch-uni-name">University ${i}</span>`;
            list.appendChild(item);
        }
    }

    function setUniversityStatus(index, name, state, items) {
        const item = document.getElementById(`batch-uni-${index}`);
        if (!item) return;
        item.className = `batch-uni-item ${state}`;
        const icons = { running: '⟳', done: '✓', error: '✗', pending: '○' };
        item.querySelector('.batch-uni-icon').textContent = icons[state] || '○';
        item.querySelector('.batch-uni-name').textContent = name;
        items[index] = state;
    }

    function updateBatchProgress(done, total) {
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        document.getElementById('batchProgressLabel').textContent = `University ${done} of ${total}`;
        document.getElementById('batchProgressPct').textContent = `${pct}%`;
        document.getElementById('batchProgressBar').style.width = `${pct}%`;
    }

    function appendResults(universityName, files) {
        const container = document.getElementById('results');
        const list = document.getElementById('fileList');
        container.classList.remove('hidden');

        const header = document.createElement('div');
        header.className = 'batch-results-header';
        header.textContent = universityName;
        list.appendChild(header);

        const fileTypes = {
            'csv': { icon: '📊', label: 'CSV Data' },
            'excel': { icon: '📗', label: 'Excel Report' },
            'json': { icon: '📦', label: 'JSON Data' }
        };

        for (const [key, path] of Object.entries(files)) {
            let typeKey = 'json';
            if (key.includes('csv')) typeKey = 'csv';
            else if (key.includes('xlsx') || key.includes('excel')) typeKey = 'excel';
            const meta = fileTypes[typeKey] || { icon: '📄', label: key.toUpperCase() };
            const filename = path.split('/').pop();

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
            list.appendChild(link);
        }
    }

    // --- Shared SSE Stream Consumer ---
    async function consumeStream(response, handlers) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        const startTime = handlers.startTime || Date.now();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = JSON.parse(line.slice(6));

                if (data.status === 'progress') handlers.onProgress(data);
                else if (data.status === 'warning') handlers.onWarning(data);
                else if (data.status === 'complete') { handlers.onComplete(data, startTime); return; }
                else if (data.error) handlers.onError(data.error);
            }
        }
    }

    // --- Shared UI Helpers ---

    function resetStatusArea() {
        document.getElementById('statusArea').classList.remove('hidden');
        document.getElementById('results').classList.add('hidden');
        document.getElementById('fileList').innerHTML = '';
        document.getElementById('logs').innerHTML = '<div class="log-line system">> System ready.</div>';
        document.getElementById('batchUniversityList').innerHTML = '';
        updateBatchProgress(0, 0);
    }

    function setLoading(btn, isLoading, idleText) {
        btn.disabled = isLoading;
        const loader = btn.querySelector('.btn-loader');
        const text = btn.querySelector('.btn-text');
        if (isLoading) {
            loader.classList.remove('hidden');
            text.textContent = 'Processing...';
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        } else {
            loader.classList.add('hidden');
            text.textContent = idleText;
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
        list.innerHTML = '';

        const fileTypes = {
            'csv': { icon: '📊', label: 'CSV Data' },
            'excel': { icon: '📗', label: 'Excel Report' },
            'json': { icon: '📦', label: 'JSON Data' }
        };

        for (const [key, path] of Object.entries(files)) {
            let typeKey = 'json';
            if (key.includes('csv')) typeKey = 'csv';
            else if (key.includes('xlsx') || key.includes('excel')) typeKey = 'excel';

            const meta = fileTypes[typeKey] || { icon: '📄', label: key.toUpperCase() };
            const filename = path.split('/').pop();

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
        setTimeout(() => { element.style.borderColor = 'var(--surface-border)'; }, 2000);
    }
});
