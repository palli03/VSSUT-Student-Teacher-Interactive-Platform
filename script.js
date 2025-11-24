// script.js (Replace existing content)

document.addEventListener('DOMContentLoaded', function() {
    
    const listConfig = [
        { id: 'webinarList', inputId: 'webinarInput', storageKey: 'webinars' },
        { id: 'internshipList', inputId: 'internshipInput', storageKey: 'internships' },
        { id: 'projectList', inputId: 'projectInput', storageKey: 'projects' },
        { id: 'hackathonList', inputId: 'hackathonInput', storageKey: 'hackathons' }
    ];

    // --- Dynamic List Management Functions ---

    function createListItem(text, listId) {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'list-item';
        itemDiv.innerHTML = `
            <span>${text}</span>
            <button type="button" class="remove-btn">Remove</button>
        `;
        itemDiv.querySelector('.remove-btn').addEventListener('click', function() {
            itemDiv.remove();
        });
        document.getElementById(listId).appendChild(itemDiv);
    }

    function initializeAddButtons() {
        document.querySelectorAll('.add-btn').forEach(button => {
            button.addEventListener('click', function() {
                const listId = this.getAttribute('data-list-id');
                const inputId = this.getAttribute('data-input-id');
                const inputElement = document.getElementById(inputId);
                const value = inputElement.value.trim();

                if (value) {
                    createListItem(value, listId);
                    inputElement.value = ''; // Clear input
                } else {
                    alert('Please enter a value before adding.');
                }
            });
        });
    }
    
    // --- Load Data Function ---

    function loadProfileData() {
        const savedDataString = localStorage.getItem('studentProfileData');
        if (savedDataString) {
            const data = JSON.parse(savedDataString);
            
            // Personal Info (Existing)
            document.getElementById('fullName').value = data.fullName || '';
            document.getElementById('email').value = data.email || 'user@example.com';
            document.getElementById('phone').value = data.phone || '';
            document.getElementById('address').value = data.address || '';
            document.getElementById('dob').value = data.dob || '';

            // Educational Details (Existing)
            document.getElementById('institution').value = data.institution || '';
            document.getElementById('rollNumber').value = data.rollNumber || '';
            document.getElementById('degree').value = data.degree || '';
            document.getElementById('branch').value = data.branch || '';

            // Experience and Skills (New Static Fields)
            document.getElementById('skills').value = data.skills || '';
            document.getElementById('techLanguages').value = data.techLanguages || '';
            document.getElementById('placementStatus').value = data.placementStatus || '';

            // Dropdowns (Existing Helper Function)
            function setSelectByText(selectId, textValue) {
                const select = document.getElementById(selectId);
                if (!select) return;
                for (let i = 0; i < select.options.length; i++) {
                    if (select.options[i].text === textValue) {
                        select.value = select.options[i].value;
                        return;
                    }
                }
                // Fallback for placementStatus if it saved a value (e.g. 'not_placed')
                select.value = textValue;
            }
            setSelectByText('year', data.year);
            setSelectByText('semester', data.semester);
            
            // Dynamic Lists (New List Data)
            listConfig.forEach(config => {
                if (data[config.storageKey] && Array.isArray(data[config.storageKey])) {
                    data[config.storageKey].forEach(item => {
                        createListItem(item, config.id);
                    });
                }
            });
        }
    }
    
    // --- Form Submission Handler ---

    document.getElementById('editProfileForm').addEventListener('submit', function(event) {
        event.preventDefault(); 
        
        // Basic Validation (You can expand this)
        const fullName = document.getElementById('fullName').value.trim();
        const phone = document.getElementById('phone').value.trim();
        
        if (fullName === "" || phone.length < 10) {
            alert('Please check your input fields.');
            return;
        }

        // Helper to collect list data
        const collectedListData = {};
        listConfig.forEach(config => {
            collectedListData[config.storageKey] = Array.from(
                document.getElementById(config.id).querySelectorAll('.list-item span')
            ).map(span => span.textContent);
        });

        // --- 💾 Save Data to Local Storage (Updated to include all fields) ---
        const profileData = {
            // Personal Info
            fullName: fullName,
            email: document.getElementById('email').value || 'user@example.com',
            phone: phone,
            address: document.getElementById('address').value,
            dob: document.getElementById('dob').value, 
            
            // Educational Details
            institution: document.getElementById('institution').value,
            rollNumber: document.getElementById('rollNumber').value,
            degree: document.getElementById('degree').value,
            branch: document.getElementById('branch').value,
            year: document.getElementById('year').options[document.getElementById('year').selectedIndex].text,
            semester: document.getElementById('semester').options[document.getElementById('semester').selectedIndex].text,
            
            // Experience and Skills (New Static Fields)
            skills: document.getElementById('skills').value,
            techLanguages: document.getElementById('techLanguages').value,
            placementStatus: document.getElementById('placementStatus').value,
            
            // Dynamic Lists (New List Data)
            ...collectedListData
        };

        localStorage.setItem('studentProfileData', JSON.stringify(profileData));

        alert('Profile updated and saved successfully! Redirecting to Dashboard...');
        
        // Redirect to the dashboard page (dash.html)
        // window.location.href = 'dash.html'; 
    });

    // --- Initial Setup ---
    loadProfileData();
    initializeAddButtons();
    
    // Cancel button redirect
    document.querySelector('.btn.secondary').addEventListener('click', function() {
        if (confirm('Are you sure you want to discard changes?')) {
            window.location.href = 'dash.html'; // Go back to dashboard
        }
    });
});