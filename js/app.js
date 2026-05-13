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
            const email =
localStorage.getItem(
    "userEmail"
);

            const latitude =
            position.coords.latitude;

            const longitude =
            position.coords.longitude;

            const timestamp =
            new Date().toLocaleString();

            const formData = new FormData();

            formData.append("image", file);
            formData.append("latitude", latitude);
            formData.append("longitude", longitude);
            formData.append("timestamp", timestamp);
            formData.append("priority", priority);
            formData.append(
    "email",
    email
);

            try{

                const response = await fetch(
                    "https://larvae-lens-backend.onrender.com/upload",
                    {
                        method:"POST",
                        body:formData
                    }
                );

                const data = await response.json();

                alert(
`Report Uploaded Successfully

Risk Level: ${data.risk_level}`
);

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

    const table =
    document.getElementById("reportTable");
    if(!table){
    return;
}

    table.innerHTML = "";

    reports.reverse().forEach(report => {

        table.innerHTML += `

        <tr>

            <td>
                ${report.image}
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

        key: "rzp_test_09f1RW6egHRwCD",

        amount: 2000,

        currency: "INR",

        name: "Larvae Lens",

        description:
        "Priority Municipal Escalation",

        image:
        "https://cdn-icons-png.flaticon.com/512/616/616408.png",

        handler: function(response){

            alert(

`Payment Successful

Priority Report Activated`
            );

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

        {
            method:"PUT"
        }

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

            `<b>Risk:</b> ${report.risk_level}
            <br>
            <b>Status:</b> ${report.status}`

        );

    });

}
if(window.location.pathname.includes("admindashboard.html")){

    loadReports();

    loadMap();

}