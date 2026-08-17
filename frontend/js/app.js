import { ENV } from './config.js';

async function submitReport(priority=false){
    const imageInput = document.getElementById("imageInput");
    const file = imageInput.files[0];

    if(!file){
        alert("Please select an image");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async(position)=>{
            const email = localStorage.getItem("userEmail");
            const userName = localStorage.getItem("userName");

            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;
            const timestamp = new Date().toLocaleString();

            const formData = new FormData();
            formData.append("image", file);
            formData.append("latitude", latitude);
            formData.append("longitude", longitude);
            formData.append("timestamp", timestamp);
            formData.append("priority", priority);
            formData.append("email", email);
            formData.append("user_name", userName);

            try{
                const response = await fetch(
                    `${ENV.API_BASE_URL}/upload`,
                    {
                        method:"POST",
                        body:formData
                    }
                );

                const data = await response.json();
                alert(`Report Uploaded Successfully\n\nRisk Level: ${data.risk_level}`);
                console.log(data);
            }
            catch(error){
                console.log(error);
                alert("Upload failed");
            }
        },
        ()=>{
            alert("Location access denied");
        }
    );
}

async function loadReports(){
    const response = await fetch(`${ENV.API_BASE_URL}/reports`);
    const reports = await response.json();
    console.log(reports);

    const table = document.getElementById("reportTable");
    if(!table){
        return;
    }

    table.innerHTML = "";

    reports.sort((a,b)=>
        new Date(b.timestamp) - new Date(a.timestamp)
    ).forEach(report => {
        table.innerHTML += `
        <tr>
           <td>
                <img
                    src="${ENV.API_BASE_URL}/uploads/${report.image}"
                    width="120"
                    height="80"
                    style="border-radius:10px;object-fit:cover;"
                    onerror="this.src='https://placehold.co/120x80?text=No+Image'"
                />
            </td>
            <td class="${report.risk_level.toLowerCase()}">
                ${report.risk_level}
                ${report.priority == "true"
                    ? '<span class="badge bg-danger">PRIORITY</span>'
                    : ''
                }
            </td>
            <td>
                ${report.status}
            </td>
            <td>
                <button
                    class="btn btn-success"
                    onclick="markCompleted('${report.id}')">
                    Complete
                </button>
            </td>
        </tr>
        `;
    });
}

function payNow(){
    const options = {
        key: ENV.RAZORPAY_KEY_ID,
        amount: 2000,
        currency: "INR",
        name: "Larvae Lens",
        description: "Priority Municipal Escalation",
        image: "https://cdn-icons-png.flaticon.com/512/616/616408.png",
        handler: function(response){
            alert("Payment Successful\n\nPriority Report Activated");
            console.log(response);
        },
        theme: {
            color: "#00ffaa"
        }
    };

    const rzp = new Razorpay(options);
    rzp.open();
}

async function markCompleted(id){
    await fetch(
        `${ENV.API_BASE_URL}/update-status/${id}`,
        {
            method:"PUT"
        }
    );
    loadReports();
}

async function loadMap(){
    const response = await fetch(`${ENV.API_BASE_URL}/reports`);
    const reports = await response.json();

    // Create map
    const map = L.map('map').setView(
        [23.3441, 85.3096],
        5
    );

    // OpenStreetMap
    L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {
            attribution: 'OpenStreetMap'
        }
    ).addTo(map);

    // Add markers
    reports.forEach(report => {
        let color;
        if(report.risk_level == "HIGH"){
            color = "red";
        }
        else if(report.risk_level == "MEDIUM"){
            color = "orange";
        }
        else{
            color = "green";
        }

        const marker = L.circleMarker(
            [
                parseFloat(report.latitude),
                parseFloat(report.longitude)
            ],
            {
                color: color,
                radius: 10
            }
        ).addTo(map);

        marker.bindPopup(
            `<b>Risk:</b> ${report.risk_level}<br><b>Status:</b> ${report.status}`
        );
    });
}

// Initialization check based on page path
if(window.location.pathname.includes("admindashboard.html")){
    loadReports();
    loadMap();
}

// Bind to window object for legacy HTML event handlers
window.submitReport = submitReport;
window.loadReports = loadReports;
window.payNow = payNow;
window.markCompleted = markCompleted;
window.loadMap = loadMap;