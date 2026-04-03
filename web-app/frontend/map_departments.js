document.addEventListener('DOMContentLoaded', () => {
    const universityNameInput = document.getElementById('universityName');
    const mapBtn = document.getElementById('mapBtn');
    const statusArea = document.getElementById('statusArea');
    const statusBadge = document.getElementById('statusBadge');
    const logs = document.getElementById('logs');
    const results = document.getElementById('results');
    const fileList = document.getElementById('fileList');

    let isMapping = false;

    mapBtn.addEventListener('click', async () => {
        const universityName = universityNameInput.value.trim();
        const programsFile = document.getElementById('programsFile').files[0];
        const departmentsFile = document.getElementById('departmentsFile').files[0];
        
        if (!programsFile || !departmentsFile) {
            alert('Please select both Programs and Departments CSV files.');
            return;
        }

        if (isMapping) return;

        // Reset UI
        isMapping = true;
        mapBtn.disabled = true;
        mapBtn.querySelector('.btn-loader').classList.remove('hidden');
        mapBtn.querySelector('.btn-text').textContent = 'Mapping...';
        
        statusArea.classList.remove('hidden');
        results.classList.add('hidden');
        fileList.innerHTML = '';
        logs.innerHTML = '<div class="log-line system">> Preparing files for upload...</div>';
        statusBadge.textContent = 'Mapping';
        statusBadge.className = 'badge';

        try {
            const formData = new FormData();
            formData.append('programs_file', programsFile);
            formData.append('departments_file', departmentsFile);
            formData.append('university_name', universityName || 'Uploaded');

            const response = await fetch('/api/map_departments', {
                method: 'POST',
                body: formData // Fetch handles Content-Type automatically for FormData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to start mapping');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.substring(6));
                        handleUpdate(data);
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            addLog(`Error: ${error.message}`, 'error');
            statusBadge.textContent = 'Error';
            statusBadge.className = 'badge error';
        } finally {
            isMapping = false;
            mapBtn.disabled = false;
            mapBtn.querySelector('.btn-loader').classList.add('hidden');
            mapBtn.querySelector('.btn-text').textContent = 'Start Mapping';
        }
    });

    function handleUpdate(data) {
        if (data.status === 'progress') {
            addLog(data.message);
        } else if (data.status === 'warning') {
            addLog(data.message, 'warning');
        } else if (data.status === 'error') {
            addLog(data.message, 'error');
            statusBadge.textContent = 'Error';
            statusBadge.className = 'badge error';
        } else if (data.status === 'complete') {
            addLog(data.message, 'success');
            statusBadge.textContent = 'Complete';
            statusBadge.className = 'badge success';
            showResults(data.files);
        }
    }

    function addLog(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        line.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        
        logs.appendChild(line);
        logs.scrollTop = logs.scrollHeight;
    }

    function showResults(files) {
        results.classList.remove('hidden');
        
        Object.entries(files).forEach(([key, url]) => {
            const card = document.createElement('div');
            card.className = 'file-card';
            
            const name = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const filename = url.split('/').pop();

            card.innerHTML = `
                <div class="file-info">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    <span>${filename}</span>
                </div>
                <a href="${url}" class="download-btn" download>
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                </a>
            `;
            fileList.appendChild(card);
        });
    }
});
