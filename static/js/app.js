/**
 * Human Validation Web App Frontend Application Script
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const registrationScreen = document.getElementById('registrationScreen');
    const reviewScreen = document.getElementById('reviewScreen');
    const finalReviewScreen = document.getElementById('finalReviewScreen');
    const completedScreen = document.getElementById('completedScreen');

    const registrationForm = document.getElementById('registrationForm');
    const registrationError = document.getElementById('registrationError');
    const btnRegister = document.getElementById('btnRegister');
    const isAnonymous = document.getElementById('isAnonymous');
    const reviewerNameLabel = document.getElementById('reviewerNameLabel');
    const reviewerNameHelp = document.getElementById('reviewerNameHelp');
    const reviewerIdInput = document.getElementById('reviewerId');
    const reviewerCredentialsInput = document.getElementById('reviewerCredentials');
    const reviewerCredentialsHelp = document.getElementById('reviewerCredentialsHelp');

    const reviewerBadge = document.getElementById('reviewerBadge');
    const badgeReviewerId = document.getElementById('badgeReviewerId');
    const badgeChunk = document.getElementById('badgeChunk');

    // Reviewer UI Elements
    const caseStepIndicator = document.getElementById('caseStepIndicator');
    const globalCaseIndex = document.getElementById('globalCaseIndex');
    const progressBar = document.getElementById('progressBar');
    
    const displayFilename = document.getElementById('displayFilename');
    const displayTextMainInfo = document.getElementById('displayTextMainInfo');
    const displayRawModelResponse = document.getElementById('displayRawModelResponse');

    const radioFine = document.getElementById('radioFine');
    const radioProblem = document.getElementById('radioProblem');
    const radioUnclear = document.getElementById('radioUnclear');
    const problemDescContainer = document.getElementById('problemDescContainer');
    const problemDescription = document.getElementById('problemDescription');

    const btnPrevCase = document.getElementById('btnPrevCase');
    const btnNextCase = document.getElementById('btnNextCase');
    const btnSubmitAll = document.getElementById('btnSubmitAll');
    const reviewSummary = document.getElementById('reviewSummary');
    const btnBackToCases = document.getElementById('btnBackToCases');
    const btnSubmitForReview = document.getElementById('btnSubmitForReview');

    // Application State
    let currentReviewer = null;
    let assignedCases = [];
    let currentCasePointer = 0; // 0..9
    let reviewsDraft = {}; // Key: case_index -> { review_result, problem_description }

    // Check for saved session in localStorage
    initSession();

    function initSession() {
        const savedReviewerId = localStorage.getItem('legal_reviewer_id');
        if (savedReviewerId) {
            resumeSession(savedReviewerId);
        }
    }

    async function resumeSession(reviewerId) {
        try {
            const response = await fetch(`/api/reviewer/${encodeURIComponent(reviewerId)}`);
            const data = await response.json();

            if (data.success) {
                currentReviewer = data.reviewer;
                assignedCases = data.cases;
                localStorage.setItem('legal_reviewer_id', reviewerId);
                
                // Load local draft reviews
                loadLocalDraft(reviewerId);

                // Populate saved reviews from server if any
                if (data.saved_reviews && data.saved_reviews.length > 0) {
                    data.saved_reviews.forEach(r => {
                        reviewsDraft[r.case_index] = {
                            review_result: r.review_result,
                            problem_description: r.problem_description || ''
                        };
                    });
                }

                if (currentReviewer.status === 'completed') {
                    showScreen(completedScreen);
                } else {
                    renderReviewerBadge();
                    startReviewFlow();
                }
            } else {
                localStorage.removeItem('legal_reviewer_id');
            }
        } catch (err) {
            console.error('Session resume error:', err);
        }
    }

    // Registration Form Submit Handler
    registrationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();

        const reviewerId = reviewerIdInput.value.trim();
        const credentials = reviewerCredentialsInput.value.trim();
        const anonymous = isAnonymous.checked;

        if (!reviewerId) {
            showError(anonymous ? 'Please enter a unique anonymous username.' : 'Please enter your name.');
            return;
        }

        if (!credentials) {
            showError('Please enter your genuine qualifications or professional credentials.');
            return;
        }

        btnRegister.disabled = true;
        btnRegister.textContent = 'Allocating Chunk...';

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    reviewer_id: reviewerId,
                    name: reviewerId,
                    credentials: credentials,
                    is_anonymous: anonymous
                })
            });

            const data = await response.json();

            if (data.success) {
                currentReviewer = data.reviewer;
                assignedCases = data.cases;
                localStorage.setItem('legal_reviewer_id', reviewerId);
                
                renderReviewerBadge();
                startReviewFlow();
            } else if (data.existing_reviewer) {
                await resumeSession(reviewerId);
            } else {
                showError(data.error || 'Failed to register reviewer.');
            }
        } catch (err) {
            showError('Network or server error occurred. Please try again.');
        } finally {
            btnRegister.disabled = false;
            btnRegister.textContent = 'Start Reviewing (Get 10 Cases) →';
        }
    });

    isAnonymous.addEventListener('change', () => {
        if (isAnonymous.checked) {
            reviewerNameLabel.innerHTML = 'Enter a unique anonymous username <span class="required">*</span>';
            reviewerIdInput.placeholder = 'e.g. BlueTiger27';
            reviewerNameHelp.textContent = 'Choose a fake name you can use to continue this review later. It must be unique.';
            reviewerCredentialsHelp.textContent = 'Please enter genuine credentials only; they are collected separately from your anonymous username.';
            reviewerIdInput.autocomplete = 'off';
        } else {
            reviewerNameLabel.innerHTML = 'Enter your name <span class="required">*</span>';
            reviewerIdInput.placeholder = 'e.g. Asha Sharma';
            reviewerNameHelp.textContent = 'Use the same name later if you need to continue an unfinished review on this device.';
            reviewerCredentialsHelp.textContent = 'Please enter your genuine qualifications or professional credentials. Do not enter fake credentials.';
            reviewerIdInput.autocomplete = 'name';
        }
    });

    function renderReviewerBadge() {
        if (!currentReviewer) return;
        badgeReviewerId.textContent = currentReviewer.reviewer_id;
        badgeChunk.textContent = `Chunk ${currentReviewer.chunk_index + 1} of ${currentReviewer.total_chunks || 50}`;
        reviewerBadge.classList.remove('hidden');
    }

    function startReviewFlow() {
        showScreen(reviewScreen);
        currentCasePointer = 0;
        renderCurrentCase();
    }

    function renderCurrentCase() {
        if (assignedCases.length === 0) return;

        const currentCase = assignedCases[currentCasePointer];

        // Update progress UI
        caseStepIndicator.textContent = `Case ${currentCasePointer + 1} of ${assignedCases.length}`;
        globalCaseIndex.textContent = `Overall Case #${currentCase.case_index + 1}`;
        const pct = ((currentCasePointer + 1) / assignedCases.length) * 100;
        progressBar.style.width = `${pct}%`;

        // Update case detail UI
        displayFilename.textContent = currentCase.filename || 'Untitled Case';
        displayTextMainInfo.textContent = currentCase.text_main_info || 'No case text available.';
        displayRawModelResponse.textContent = currentCase.raw_model_response || 'No model response available.';

        // Load saved draft response for this case pointer
        const savedResponse = reviewsDraft[currentCase.case_index] || { review_result: '', problem_description: '' };

        if (savedResponse.review_result === 'Fine') {
            radioFine.checked = true;
            problemDescContainer.classList.add('hidden');
        } else if (savedResponse.review_result === 'Problem') {
            radioProblem.checked = true;
            problemDescContainer.classList.remove('hidden');
        } else if (savedResponse.review_result === 'Unclear/Vague') {
            radioUnclear.checked = true;
            problemDescContainer.classList.add('hidden');
        } else {
            radioFine.checked = false;
            radioProblem.checked = false;
            radioUnclear.checked = false;
            problemDescContainer.classList.add('hidden');
        }

        problemDescription.value = savedResponse.problem_description || '';

        // Navigation button states
        btnPrevCase.disabled = (currentCasePointer === 0);

        if (currentCasePointer === assignedCases.length - 1) {
            btnNextCase.classList.add('hidden');
            btnSubmitAll.classList.remove('hidden');
        } else {
            btnNextCase.classList.remove('hidden');
            btnSubmitAll.classList.add('hidden');
        }

        // Scroll to top of case text
        displayTextMainInfo.scrollTop = 0;
        displayRawModelResponse.scrollTop = 0;
    }

    // Radio change handlers
    document.querySelectorAll('input[name="reviewResult"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'Problem') {
                problemDescContainer.classList.remove('hidden');
            } else {
                problemDescContainer.classList.add('hidden');
            }
            saveCurrentCaseDraft();
        });
    });

    problemDescription.addEventListener('input', () => {
        saveCurrentCaseDraft();
    });

    function saveCurrentCaseDraft() {
        if (!assignedCases || assignedCases.length === 0) return;
        const currentCase = assignedCases[currentCasePointer];
        
        let selectedResult = '';
        if (radioFine.checked) selectedResult = 'Fine';
        if (radioProblem.checked) selectedResult = 'Problem';
        if (radioUnclear.checked) selectedResult = 'Unclear/Vague';

        reviewsDraft[currentCase.case_index] = {
            review_result: selectedResult,
            problem_description: problemDescription.value.trim()
        };

        // Persist draft in localStorage
        if (currentReviewer) {
            localStorage.setItem(`draft_${currentReviewer.reviewer_id}`, JSON.stringify(reviewsDraft));
        }
    }

    function loadLocalDraft(reviewerId) {
        const raw = localStorage.getItem(`draft_${reviewerId}`);
        if (raw) {
            try {
                reviewsDraft = JSON.parse(raw);
            } catch (e) {}
        }
    }

    function validateCurrentCaseInput() {
        saveCurrentCaseDraft();
        const currentCase = assignedCases[currentCasePointer];
        const draft = reviewsDraft[currentCase.case_index];

        if (!draft || !draft.review_result) {
            alert('Please choose Fine, Problem, or Don\'t know / unclear before proceeding.');
            return false;
        }

        if (draft.review_result === 'Problem' && !draft.problem_description) {
            alert('Please provide a brief description of the problem.');
            return false;
        }

        return true;
    }

    // Next Button Click Handler
    btnNextCase.addEventListener('click', () => {
        if (validateCurrentCaseInput()) {
            if (currentCasePointer < assignedCases.length - 1) {
                currentCasePointer++;
                renderCurrentCase();
            }
        }
    });

    // Previous Button Click Handler
    btnPrevCase.addEventListener('click', () => {
        saveCurrentCaseDraft();
        if (currentCasePointer > 0) {
            currentCasePointer--;
            renderCurrentCase();
        }
    });

    // Move to the final review page after all ten responses are complete.
    btnSubmitAll.addEventListener('click', () => {
        if (!validateCurrentCaseInput()) return;

        // Verify all 10 cases have responses
        for (let i = 0; i < assignedCases.length; i++) {
            const c = assignedCases[i];
            const d = reviewsDraft[c.case_index];
            if (!d || !d.review_result) {
                alert(`Case #${i + 1} (${c.filename}) has not been answered yet. Please review all 10 cases.`);
                currentCasePointer = i;
                renderCurrentCase();
                return;
            }
        }

        renderFinalReview();
        showScreen(finalReviewScreen);
    });

    function renderFinalReview() {
        reviewSummary.replaceChildren();

        assignedCases.forEach((caseItem, index) => {
            const draft = reviewsDraft[caseItem.case_index];
            const row = document.createElement('article');
            row.className = 'summary-row';

            const caseInfo = document.createElement('div');
            caseInfo.className = 'summary-case';
            const title = document.createElement('strong');
            title.textContent = `Case ${index + 1}`;
            const filename = document.createElement('span');
            filename.textContent = caseItem.filename || 'Untitled case';
            caseInfo.append(title, filename);

            const answer = document.createElement('span');
            answer.className = 'summary-answer';
            answer.textContent = draft.review_result === 'Unclear/Vague'
                ? "Don't know / unclear or vague"
                : draft.review_result;

            const editButton = document.createElement('button');
            editButton.type = 'button';
            editButton.className = 'btn btn-secondary';
            editButton.textContent = 'Edit';
            editButton.addEventListener('click', () => {
                currentCasePointer = index;
                showScreen(reviewScreen);
                renderCurrentCase();
            });

            row.append(caseInfo, answer, editButton);
            reviewSummary.append(row);
        });
    }

    btnBackToCases.addEventListener('click', () => {
        currentCasePointer = assignedCases.length - 1;
        showScreen(reviewScreen);
        renderCurrentCase();
    });

    // Submit only after the reviewer has checked the final answer summary.
    btnSubmitForReview.addEventListener('click', async () => {
        if (!confirm('Submit these 10 legal case reviews for final review?')) return;

        btnSubmitForReview.disabled = true;
        btnSubmitForReview.textContent = 'Submitting Reviews...';

        const payloadReviews = assignedCases.map(c => {
            const d = reviewsDraft[c.case_index];
            return {
                case_index: c.case_index,
                filename: c.filename,
                review_result: d.review_result,
                problem_description: d.problem_description || ''
            };
        });

        try {
            const response = await fetch('/api/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    reviewer_id: currentReviewer.reviewer_id,
                    reviews: payloadReviews
                })
            });

            const data = await response.json();

            if (data.success) {
                localStorage.removeItem(`draft_${currentReviewer.reviewer_id}`);
                showScreen(completedScreen);
            } else {
                alert(data.error || 'Failed to submit reviews.');
            }
        } catch (err) {
            alert('Server error occurred during submission. Please try again.');
        } finally {
            btnSubmitForReview.disabled = false;
            btnSubmitForReview.textContent = 'Submit for Review';
        }
    });

    // Utility Screen Switcher
    function showScreen(targetScreen) {
        [registrationScreen, reviewScreen, finalReviewScreen, completedScreen].forEach(s => s.classList.add('hidden'));
        targetScreen.classList.remove('hidden');
    }

    function showError(msg) {
        registrationError.textContent = msg;
        registrationError.classList.remove('hidden');
    }

    function hideError() {
        registrationError.classList.add('hidden');
    }
});
