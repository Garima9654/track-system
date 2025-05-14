from flask import Flask, render_template_string, request, jsonify
import requests

app = Flask(__name__)

MAX_TRACKING_IDS = 20

# HTML template with embedded CSS and JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Delhivery Tracker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        .tracker-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-height: 100px;
            margin-bottom: 10px;
        }
        button {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #2980b9;
        }
        .error {
            color: #e74c3c;
            margin: 10px 0;
        }
        .result-card {
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 10px;
        }
        .status-delivered { background-color: #2ecc71; color: white; }
        .status-transit { background-color: #f39c12; color: white; }
        .status-pending { background-color: #95a5a6; color: white; }
        .timeline {
            margin-top: 15px;
            border-left: 2px solid #3498db;
            padding-left: 20px;
        }
        .timeline-event {
            margin-bottom: 10px;
            position: relative;
            padding-left: 20px;
        }
        .timeline-event:before {
            content: '';
            position: absolute;
            left: -11px;
            top: 6px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #3498db;
        }
        .loading {
            text-align: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <h1>Delhivery Package Tracker</h1>
    
    <div class="tracker-form">
        <form id="trackingForm">
            <label for="trackIds">Enter Tracking IDs (max 20, separated by commas or new lines):</label><br>
            <textarea id="trackIds" name="trackIds" placeholder="31067110118823, 31067110115345"></textarea><br>
            <button type="submit">Track Packages</button>
        </form>
        <div id="error" class="error"></div>
    </div>
    
    <div id="results"></div>
    
    <script>
        document.getElementById('trackingForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const trackIds = document.getElementById('trackIds').value;
            const errorDiv = document.getElementById('error');
            const resultsDiv = document.getElementById('results');
            
            errorDiv.textContent = '';
            resultsDiv.innerHTML = '<div class="loading">Tracking packages...</div>';
            
            try {
                const response = await fetch('/track', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ trackIds: trackIds })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    errorDiv.textContent = data.error;
                    resultsDiv.innerHTML = '';
                    return;
                }
                
                if (data.length === 0) {
                    resultsDiv.innerHTML = '<div class="result-card">No tracking results found</div>';
                    return;
                }
                
                resultsDiv.innerHTML = '';
                
                data.forEach(result => {
                    if (!result.data || result.data.length === 0) return;
                    
                    const packageData = result.data[0];
                    const status = packageData.status?.status || 'UNKNOWN';
                    
                    let statusClass = 'status-pending';
                    if (status.includes('DELIVERED')) statusClass = 'status-delivered';
                    else if (status.includes('TRANSIT') || status.includes('REACHED')) statusClass = 'status-transit';
                    
                    let html = `
                        <div class="result-card">
                            <h3>Tracking ID: ${packageData.awb || 'N/A'}</h3>
                            <div>
                                <span class="status-badge ${statusClass}">${status.replace(/_/g, ' ')}</span>
                                <span>${packageData.status?.statusDateTime || ''}</span>
                            </div>
                            <p>${packageData.status?.instructions || 'No instructions available'}</p>
                            <p>Delivery Date: ${packageData.deliveryDate || 'Not specified'}</p>
                    `;
                    
                    if (packageData.trackingStates && packageData.trackingStates.length > 0) {
                        html += `<div class="timeline"><h4>Tracking History:</h4>`;
                        
                        packageData.trackingStates.forEach(state => {
                            html += `<div class="timeline-event">
                                <strong>${state.label}</strong>`;
                            
                            if (state.scans && state.scans.length > 0) {
                                state.scans.forEach(scan => {
                                    html += `<div>
                                        <p>${scan.scanNslRemark || 'No remark'}</p>
                                        <small>${scan.cityLocation || ''} - ${scan.scanDateTime || ''}</small>
                                    </div>`;
                                });
                            }
                            
                            html += `</div>`;
                        });
                        
                        html += `</div>`;
                    }
                    
                    html += `</div>`;
                    resultsDiv.innerHTML += html;
                });
                
            } catch (err) {
                errorDiv.textContent = 'Failed to track packages. Please try again.';
                resultsDiv.innerHTML = '';
                console.error(err);
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/track', methods=['POST'])
def track_packages():
    try:
        data = request.get_json()
        if not data or 'trackIds' not in data:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Parse tracking IDs (comma, space, or newline separated)
        track_ids = [tid.strip() for tid in data['trackIds'].replace('\n', ',').split(',') if tid.strip()]
        
        if not track_ids:
            return jsonify({'error': 'Please enter at least one tracking ID'}), 400
        
        if len(track_ids) > MAX_TRACKING_IDS:
            return jsonify({'error': f'Maximum {MAX_TRACKING_IDS} tracking IDs allowed'}), 400
        
        results = []
        for track_id in track_ids:
            try:
                response = requests.get(
                    f'https://dlv-api.delhivery.com/v3/unified-tracking?wbn={track_id}',
                    headers={
                        'accept': 'application/json, text/plain, */*',
                        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                        'origin': 'https://www.delhivery.com',
                        'referer': 'https://www.delhivery.com/',
                        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
                    }
                )
                results.append(response.json())
            except Exception as e:
                print(f"Error tracking {track_id}: {str(e)}")
                results.append({'error': f'Failed to track ID {track_id}'})
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Error in track_packages: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)