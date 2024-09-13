document.getElementById('queryForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const prompt = document.getElementById('prompt').value;
    const resultDiv = document.getElementById('result');
    const startTime = performance.now();

    try {
        const response = await fetch('http://127.0.0.1:8008/query', {  // Changed port to 8008
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt }),
        });

        const data = await response.json();
        const endTime = performance.now();
        const responseTime = endTime - startTime;

        if (response.ok) {
            resultDiv.innerHTML = `
                <p><strong>Result:</strong> ${data.result}</p>
                <p><strong>Response Time:</strong> ${responseTime.toFixed(2)} ms</p>
            `;
        } else {
            resultDiv.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${data.error}</p>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<p style="color: red;"><strong>Error:</strong> ${error.message}</p>`;
    }
});
