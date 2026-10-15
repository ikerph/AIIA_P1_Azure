let chart = null;
let histogram = null;

// Function to read and parse the CSV data
function parseCSV(csv) {
    const lines = csv.split("\n");
    const data = [];

    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim() === '') {
            continue; // skip empty lines
        }
        const line = lines[i].split(",");
        const timestamp = line[0];
        const personCount = parseInt(line[1]);
        const inferenceMs = parseFloat(line[2]);
        const cpu = parseFloat(line[3]);
        const ram = parseFloat(line[4]);

        data.push({ timestamp, personCount, inferenceMs, cpu, ram });
    }

    return data;
}

// Function to create the histogram: number of frames with 0, 1, 2... people
function createHistogram(data) {
    const counts = data.map(entry => entry.personCount);
    const maxCount = Math.max(...counts);

    const labels = [];
    const frames = [];
    for (let n = 0; n <= maxCount; n++) {
        labels.push(n);
        frames.push(counts.filter(count => count === n).length);
    }

    const ctx = document.getElementById('histogramChart').getContext('2d');

    if (histogram) {
        histogram.destroy();
    }
    histogram = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Frames',
                data: frames,
                backgroundColor: 'rgba(29, 95, 196, 0.7)',
            }]
        },
        options: {
            responsive: true,
            legend: {
                display: false
            },
            scales: {
				yAxes: [{
					ticks: {
					  beginAtZero: true,
					  precision: 0
					},
					scaleLabel: {
					  display: true,
					  labelString: 'Number of frames'
					}
				}],
				xAxes: [{
					scaleLabel: {
					  display: true,
					  labelString: 'People in the frame'
					}
				}]
            },
			animation: {
                duration: 0
            }
        }
    });
}

// Function to show other data
function showStats(data) {
    const counts = data.map(entry => entry.personCount);
    const average = counts.reduce((a, b) => a + b, 0) / counts.length;
    const averageInference = data.reduce((a, entry) => a + entry.inferenceMs, 0) / data.length;
    const last = data[data.length - 1];

    document.getElementById('statFrames').textContent = data.length;
    document.getElementById('statAvg').textContent = average.toFixed(1);
    document.getElementById('statMax').textContent = Math.max(...counts);
    document.getElementById('statInference').textContent = averageInference.toFixed(0) + ' ms';
    document.getElementById('statCpu').textContent = last.cpu + ' %';
    document.getElementById('statRam').textContent = last.ram + ' MB';
}

// Function to create and display the chart
function createChart(data) {
    // Parse timestamps and counts
    const timestamps = data.map(entry => parseTimestamp(entry.timestamp));
    const counts = data.map(entry => entry.personCount);

    // Filter out empty strings from the timestamps array
    const filteredTimestamps = timestamps.filter(timestamp => timestamp !== null);

    // Create an array of timestamps with gaps
    const interval = 1000; // 1 second in ms
    const labels = [];
    const filledCounts = [];
    let currentTimestamp = new Date(filteredTimestamps[0]);

    for (let i = 0; i < filteredTimestamps.length; i++) {
        const timestamp = filteredTimestamps[i];
        while (currentTimestamp < timestamp) {
            labels.push(currentTimestamp.toISOString());
            filledCounts.push(null); // Fill gaps with null values
            currentTimestamp = new Date(currentTimestamp.getTime() + interval);
        }
        labels.push(timestamp.toISOString());
        filledCounts.push(counts[i]);
        currentTimestamp = new Date(timestamp.getTime() + interval);
    }

    // Create the chart
    const ctx = document.getElementById('personCountChart').getContext('2d');

    // Remove the previous chart, otherwise a new one is drawn on top every second
    if (chart) {
        chart.destroy();
    }
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Person Count',
                data: filledCounts,
                borderColor: 'rgba(29, 95, 196, 1)',
                backgroundColor: 'rgba(29, 95, 196, 0.12)',
                borderWidth: 2,
                pointRadius: 2,
                lineTension: 0.2,
                fill: true,
                spanGaps: true,
            }]
        },
        options: {
            responsive: true,
            legend: {
                display: false
            },
            scales: {
				yAxes: [{
					display: true,
					ticks: {
					  beginAtZero: true,
					  precision: 0
					},
					scaleLabel: {
					  display: true,
					  labelString: 'Person count'
					}
				}],
				xAxes: [{
					display: true,
					type: 'time',
					time: {
					  unit: 'minute',
					  displayFormats: {
					    minute: 'HH:mm'
					  },
					  tooltipFormat: 'HH:mm:ss'
					},
					scaleLabel: {
					  display: true,
					  labelString: 'Time'
					}
				}]
            },
			animation: {
                // Disable the initial animation
                duration: 0 // Set animation duration to 0 milliseconds
            }
        }
    });
}

// Function to parse timestamps in "YYYY-MM-DD HH:mm:ss" format
function parseTimestamp(timestampStr) {
    if (timestampStr.trim() === '') {
        return null; // Return null for empty timestamps
    }
    const [dateStr, timeStr] = timestampStr.split(' ');
    const [year, month, day] = dateStr.split('-').map(Number);
    const [hours, minutes, seconds] = timeStr.split(':').map(Number);
    return new Date(year, month - 1, day, hours, minutes, seconds);
}


// Function to fetch new data and reload the chart
function fetchDataAndReloadChart() {
	// Fetch and process the CSV file
	fetch('database.csv', { cache: 'no-store' })
		.then(response => response.text())
		.then(csv => {
			const data = parseCSV(csv);
			if (data.length === 0) {
				return; // no frames processed
			}
			createChart(data);
			createHistogram(data);
			showStats(data);
		})
		.catch(error => {
			console.error('Error:', error);
		});
}


// Function to reload the image every second
function reloadImage() {
    const imageElement = document.getElementById('reloadImage');

    // Function to add a timestamp or random parameter to the image URL
    function addTimestampToUrl(url) {
        const timestamp = new Date().getTime(); // Get current timestamp
        return url.split('?')[0] + '?' + timestamp; // replace the old timestamp instead of adding another one
    }

    // Use setInterval to reload the image every second
    setInterval(function () {
        imageElement.src = addTimestampToUrl(imageElement.src);
		fetchDataAndReloadChart();
    }, 1000); // 1000 milliseconds = 1 second
}

// Call the reloadImage function to start reloading the image
reloadImage();
