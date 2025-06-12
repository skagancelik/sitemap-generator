document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('crawlForm');
    const urlInput = document.getElementById('urlInput');
    const submitBtn = document.getElementById('submitBtn');
    const progressDiv = document.getElementById('progress');
    const urlListDiv = document.getElementById('urlList');
    const downloadBtn = document.getElementById('downloadBtn');
    const csvBtn = document.getElementById('csvBtn');
    const resultsContainer = document.getElementById('resultsContainer');
    
    let currentSessionId = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        submitBtn.disabled = true;
        submitBtn.textContent = 'İşleniyor...';
        progressDiv.innerHTML = 'Tarama başlatılıyor...';
        urlListDiv.innerHTML = '';
        downloadBtn.style.display = 'none';
        csvBtn.style.display = 'none';
        resultsContainer.style.display = 'block';

        try {
            const response = await fetch('/crawl', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'Failed to start crawling');
            }

            currentSessionId = result.session_id;
            progressDiv.innerHTML = `Tarama başlatıldı: ${result.url}`;
            
            // Wait a moment for the server to start processing
            setTimeout(() => {
                updateProgress();
            }, 1000);
            
        } catch (error) {
            console.error('Error:', error);
            progressDiv.innerHTML = `Error: ${error.message}`;
            submitBtn.disabled = false;
            submitBtn.textContent = 'Generate Sitemap';
        }
    });

    async function updateProgress() {
        if (!currentSessionId) {
            progressDiv.innerHTML = 'No active session';
            return;
        }
        
        try {
            const response = await fetch(`/progress/${currentSessionId}`);
            const data = await response.json();
            
            if (data.error && data.error !== "Session expired or not found") {
                let errorHtml = `<div class="error-message"><strong>Hata:</strong> ${data.error}`;
                
                if (data.error_details) {
                    errorHtml += `<div class="error-details"><h4>Detay:</h4><pre>${data.error_details}</pre></div>`;
                }
                
                errorHtml += '</div>';
                progressDiv.innerHTML = errorHtml;
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sitemap Oluştur';
                return;
            }
            
            if (data.message && data.message.includes("not found")) {
                progressDiv.innerHTML = 'Session bulunamadı, yeniden başlatılıyor...';
                setTimeout(updateProgress, 2000);
                return;
            }
            
            progressDiv.innerHTML = `Sitemap oluşturuluyor: ${data.crawled_urls} URL`;

            if (data.visited_urls && data.visited_urls.length > 0) {
                updateUrlList(data.visited_urls);
            }

            if (!data.completed) {
                setTimeout(updateProgress, 1000);
            } else {
                if (data.visited_urls && data.visited_urls.length > 0) {
                    progressDiv.innerHTML = `Tamamlandı! ${data.crawled_urls} URL bulundu`;
                    downloadBtn.style.display = 'block';
                    csvBtn.style.display = 'block';
                } else {
                    progressDiv.innerHTML = `Uyarı: Taranacak URL bulunamadı`;
                }
                submitBtn.disabled = false;
                submitBtn.textContent = 'Sitemap Oluştur';
            }
        } catch (error) {
            console.error('Error:', error);
            progressDiv.innerHTML = 'An error occurred while updating progress.';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Generate Sitemap';
        }
    }

    function updateUrlList(urls) {
        urlListDiv.innerHTML = '<h3>Crawled URLs:</h3>';
        const ul = document.createElement('ul');
        urls.forEach(url => {
            const li = document.createElement('li');
            li.textContent = url;
            ul.appendChild(li);
        });
        urlListDiv.appendChild(ul);
    }

    downloadBtn.addEventListener('click', () => {
        window.location.href = '/download';
    });

    csvBtn.addEventListener('click', () => {
        if (currentSessionId) {
            window.location.href = `/download-csv/${currentSessionId}`;
        }
    });

    urlInput.addEventListener('input', () => {
        if (!urlInput.value) {
            resultsContainer.style.display = 'none';
        }
    });

    // Hide resultsContainer on page load
    resultsContainer.style.display = 'none';
});
