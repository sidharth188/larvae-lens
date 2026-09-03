import { ENV } from './config.js';

async function submitReport(priority=false){
    const imageInput=document.getElementById("imageInput");
    const file=imageInput.files[0];
    if(!file){alert("Please select an image");return;}
    
    // UI Loader State
    const submitBtn = document.querySelector(".upload-box button");
    if(submitBtn) {
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
        submitBtn.disabled = true;
    }

    navigator.geolocation.getCurrentPosition(async(position)=>{
        const email=localStorage.getItem("userEmail");
        const userName=localStorage.getItem("userName");
        const formData=new FormData();
        formData.append("image",file);formData.append("latitude",position.coords.latitude);formData.append("longitude",position.coords.longitude);formData.append("timestamp",new Date().toLocaleString());formData.append("priority",priority);formData.append("email",email);formData.append("user_name",userName);
        try{
            const response=await fetch(`${ENV.API_BASE_URL}/upload`,{method:"POST",body:formData});
            const data=await response.json();
            if(submitBtn){ submitBtn.innerHTML = 'Submit Report'; submitBtn.disabled = false; }

            if (!response.ok || data.success === false) {
                alert(`Upload failed: ${data.message || data.error || 'Unknown error'}`);
                return;
            }
            alert(`Report Uploaded Successfully\n\nRisk Level: ${data.risk_level}`);
            console.log(data);
        }catch(error){
            console.log(error);
            if(submitBtn){ submitBtn.innerHTML = 'Submit Report'; submitBtn.disabled = false; }
            alert("Network error: Upload failed");
        }
    },()=>{
        if(submitBtn){ submitBtn.innerHTML = 'Submit Report'; submitBtn.disabled = false; }
        alert("Location access denied")
    });
}

function normalizeCaseStatus(status){const value=String(status||"PENDING").toUpperCase();return value==="IN_PROGRESS"||value==="WORKING"?"IN PROGRESS":value;}
function statusBadgeClass(status){if(status==="COMPLETED")return "bg-success";if(status==="IN PROGRESS")return "bg-warning text-dark";return "bg-danger";}

async function loadReports(){
    const response=await fetch(`${ENV.API_BASE_URL}/reports`);const reports=await response.json();
    const table=document.getElementById("reportTable");if(!table)return;table.innerHTML="";
    reports.sort((a,b)=>new Date(b.timestamp)-new Date(a.timestamp)).forEach(report=>{
        const status=normalizeCaseStatus(report.status);
        const imageUrl = report.image_url || `${ENV.API_BASE_URL}/uploads/${report.image}`;
        table.innerHTML+=`<tr><td><img src="${imageUrl}" width="120" height="80" style="border-radius:10px;object-fit:cover" onerror="this.src='https://placehold.co/120x80?text=No+Image'"></td><td class="${report.risk_level.toLowerCase()}">${report.risk_level} ${report.priority === true || report.priority === "true"?'<span class="badge bg-danger">PRIORITY</span>':''}</td><td><span class="badge ${statusBadgeClass(status)}">${status}</span></td><td><div class="d-flex flex-wrap gap-2"><button class="btn btn-danger btn-sm" onclick="setCaseStatus('${report.id}','PENDING',this)">Pending</button><button class="btn btn-warning btn-sm" onclick="setCaseStatus('${report.id}','IN PROGRESS',this)">In Progress</button><button class="btn btn-success btn-sm" onclick="setCaseStatus('${report.id}','COMPLETED',this)">Completed</button></div></td></tr>`;
    });
}

async function setCaseStatus(id, status, button) {

    const row = button.closest("tr");

    if (!row) return;

    const normalizedStatus =
        status === "IN PROGRESS"
            ? "IN_PROGRESS"
            : status === "COMPLETED"
                ? "COMPLETED"
                : "PENDING";

    const buttons =
        row.querySelectorAll("button");

    buttons.forEach(btn => {
        btn.disabled = true;
    });

    try {

        const response = await fetch(
            `${ENV.API_BASE_URL}/update-status/${encodeURIComponent(id)}`,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    status: normalizedStatus
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.message ||
                data.error ||
                `HTTP ${response.status}`
            );

        }

        const displayStatus =
            normalizeCaseStatus(
                data.status || normalizedStatus
            );

        /*
         * Update the admin screen only after
         * Firestore confirms the change.
         */

        row.children[2].innerHTML =
            `<span class="badge ${statusBadgeClass(displayStatus)}">${displayStatus}</span>`;

        buttons.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        console.log(
            "Firestore status updated:",
            id,
            normalizedStatus
        );

    } catch (error) {

        console.error(
            "Status update failed:",
            error
        );

        alert(
            `Failed to update report status.\n\n${error.message}`
        );

    } finally {

        buttons.forEach(btn => {
            btn.disabled = false;
        });

    }
}

function payNow(){const options={key:ENV.RAZORPAY_KEY_ID,amount:2000,currency:"INR",name:"Larvae Lens",description:"Priority Municipal Escalation",image:"https://cdn-icons-png.flaticon.com/512/616/616408.png",handler:function(response){alert("Payment Successful\n\nPriority Report Activated");console.log(response)},theme:{color:"#00ffaa"}};new Razorpay(options).open();}
async function markCompleted(id){await fetch(`${ENV.API_BASE_URL}/update-status/${id}`,{method:"PUT"});loadReports();}

async function loadMap(){
    const response=await fetch(`${ENV.API_BASE_URL}/reports`);const reports=await response.json();
    const map=L.map('map').setView([23.3441,85.3096],5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'OpenStreetMap'}).addTo(map);
    reports.forEach(report=>{let color=report.risk_level==="HIGH"?"red":report.risk_level==="MEDIUM"?"orange":"green";const marker=L.circleMarker([parseFloat(report.latitude),parseFloat(report.longitude)],{color:color,radius:10}).addTo(map);marker.bindPopup(`<b>Risk:</b> ${report.risk_level}<br><b>Status:</b> ${normalizeCaseStatus(report.status)}`);});
}

if(window.location.pathname.includes("admindashboard.html")){loadReports();loadMap();}
window.submitReport=submitReport;window.loadReports=loadReports;window.payNow=payNow;window.markCompleted=markCompleted;window.loadMap=loadMap;window.setCaseStatus=setCaseStatus;