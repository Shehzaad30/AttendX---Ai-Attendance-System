async function getLocationAndSend() {
    if (!navigator.geolocation) {
        alert("Geolocation not supported");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async function (position) {
            const data = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };

            try {
                const response = await fetch("/save_location", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                console.log(result);
            } catch (error) {
                console.error("Error:", error);
            }
        },
        function (error) {
            alert("Location error: " + error.message);
        }
    );
}