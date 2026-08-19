async function submitReport(priority=false){

    const imageInput =
    document.getElementById("imageInput");

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
                    "https://larvae-lens-backend.onrender.com/upload",
                    { method:"POST", body:formData }
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

    const response = await fetch(
        "https://larvae-lens-backend.onrender.com/reports"
    );

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

        const status = normalizeCaseStatus(report.status);

        table.innerHTML += `
        <tr>
            <td>
                <img
                    src="https://larvae-lens-backend.onrender.com/uploads/${report.image}"
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
                    : ''}
            </td>

            <td>
                <span class="badge ${statusBadgeClass(status)}">
                    ${status}
                </span>
            </td>

            <td>
                <div class="d-flex flex-wrap gap-2">
                    <button
                        class="btn btn-danger btn-sm"
                        onclick="setCaseStatus('${report.id}','PENDING',this)">
                        Pending
                    </button>

                    <button
                        class="btn btn-warning btn-sm"
                        onclick="setCaseStatus('${report.id}','IN PROGRESS',this)">
                        In Progress
                    </button>

                    <button
                        class="btn btn-success btn-sm"
                        onclick="setCaseStatus('${report.id}','COMPLETED',this)">
                        Completed
                    </button>
                </div>
            </td>
        </tr>
        `;
    });
}


function normalizeCaseStatus(status){
    const value = String(status || "PENDING").toUpperCase();

    if(value === "IN_PROGRESS" || value === "WORKING"){
        return "IN PROGRESS";
    }

    return value;
}


function statusBadgeClass(status){
    if(status === "COMPLETED"){
        return "bg-success";
    }

    if(status === "IN PROGRESS"){
        return "bg-warning text-dark";
    }

    return "bg-danger";
}


function setCaseStatus(id, status, button){

    const row = button.closest("tr");
    if(!row){
        return;
    }

    const statusCell = row.children[2];
    statusCell.innerHTML = `
        <span class="badge ${statusBadgeClass(status)}">
            ${status}
        </span>
    `;

    row.querySelectorAll("button").forEach(btn => {
        btn.classList.remove("active");
    });

    button.classList.add("active");

    /*
       Frontend-only state for now.
       The backend currently exposes /update-status/<id>
       as a COMPLETED-only endpoint, so PENDING and
       IN PROGRESS are intentionally not sent to the API.
    */

    console.log("Case status changed:", id, status);
}


function payNow(){

    const options = {
        key: "rzp_test_09f1RW6egHRwCD",
        amount: 2000,
        currency: "INR",
        name: "Larvae Lens",
        description: "Priority Municipal Escalation",
        image: "https://cdn-icons-png.flaticon.com/512/616/616408.png",

        handler: function(response){
            alert(`Payment Successful\n\nPriority Report Activated`);
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
        `https://larvae-lens-backend.onrender.com/update-status/${id}`,
        { method:"PUT" }
    );

    loadReports();
}


if(window.location.pathname.includes("admindashboard.html")){
    loadReports();
}


async function loadMap(){

    const response = await fetch(
        "https://larvae-lens-backend.onrender.com/reports"
    );

    const reports = await response.json();

    const map = L.map('map').setView(
        [23.3441, 85.3096],
        5
    );

    L.tileLayer(
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        { attribution: 'OpenStreetMap' }
    ).addTo(map);

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
            [parseFloat(report.latitude), parseFloat(report.longitude)],
            { color: color, radius: 10 }
        ).addTo(map);

        marker.bindPopup(
            `<b>Risk:</b> ${report.risk_level}
            <br>
            <b>Status:</b> ${normalizeCaseStatus(report.status)}`
        );
    });
}


if(window.location.pathname.includes("admindashboard.html")){
    loadReports();
    loadMap();
}