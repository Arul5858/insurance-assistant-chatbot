const questions = window.ONBOARDING_QUESTIONS || [];
let step = 0;
let completed = false;
const questionText = document.getElementById('questionText');
const questionHint = document.getElementById('questionHint');
const answerArea = document.getElementById('answerArea');
const errorMessage = document.getElementById('errorMessage');
const continueBtn = document.getElementById('continueBtn');
const progressBar = document.getElementById('progressBar');
const stepLabel = document.getElementById('stepLabel');
const progressPercent = document.getElementById('progressPercent');

function renderQuestion(q, index) {
  step = index;
  questionText.textContent = q.question;
  questionHint.textContent = q.hint || '';
  errorMessage.textContent = '';
  const percent = Math.round(((index + 1) / questions.length) * 100);
  progressBar.style.width = `${percent}%`;
  stepLabel.textContent = `Question ${index + 1} of ${questions.length}`;
  progressPercent.textContent = `${percent}%`;
  answerArea.innerHTML = '';
  if (q.kind === 'number') {
    answerArea.innerHTML = '<input id="answerInput" type="number" min="18" max="100" class="form-control form-control-lg" placeholder="Enter your age">';
  } else if (q.kind === 'choice') {
    const group = document.createElement('div'); group.className = 'choice-grid';
    q.options.forEach(option => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'choice-option'; button.textContent = option;
      button.addEventListener('click', () => { group.querySelectorAll('button').forEach(b => b.classList.remove('selected')); button.classList.add('selected'); group.dataset.value = option; });
      group.appendChild(button);
    }); answerArea.appendChild(group);
  } else if (q.kind === 'budget') {
    answerArea.innerHTML = `<div class="row g-2"><div class="col-sm-5"><select id="budgetPeriod" class="form-select form-select-lg"><option value="monthly">Monthly</option><option value="annual">Annual</option></select></div><div class="col-sm-7"><div class="input-group input-group-lg"><span class="input-group-text">₹</span><input id="answerInput" type="number" min="1" step="0.01" class="form-control" placeholder="Budget amount"></div></div></div>`;
  } else {
    answerArea.innerHTML = '<input id="answerInput" type="text" maxlength="100" class="form-control form-control-lg" placeholder="Enter your answer">';
  }
  const input = document.getElementById('answerInput'); if (input) input.focus();
}

function getAnswer() {
  const q = questions[step];
  if (q.kind === 'choice') {
    const group = answerArea.querySelector('.choice-grid');
    return { value: group?.dataset.value || '' };
  }
  const input = document.getElementById('answerInput');
  if (q.kind === 'budget') return { value: input?.value || '', period: document.getElementById('budgetPeriod')?.value };
  return { value: input?.value || '' };
}

continueBtn.addEventListener('click', async () => {
  if (completed) return;
  errorMessage.textContent = '';
  const payload = getAnswer();
  if (!payload.value) { errorMessage.textContent = 'Please provide an answer before continuing.'; return; }
  continueBtn.disabled = true; continueBtn.textContent = 'Saving...';
  try {
    const response = await fetch('/api/onboarding/answer', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Could not save your answer.');
    if (data.complete) {
      completed = true;
      step = questions.length;
      questionText.textContent = 'Your insurance profile is ready!';
      questionHint.textContent = data.message;
      answerArea.innerHTML = '<div class="success-panel">Thank you for answering all five questions. You can now chat with your Insurance Assistant.</div>';
      progressBar.style.width = '100%'; progressPercent.textContent = '100%'; stepLabel.textContent = 'Completed';
      continueBtn.textContent = 'Continue to chat';
      continueBtn.disabled = false;
      continueBtn.onclick = () => window.location.href = data.redirect;
      return;
    }
    renderQuestion(data.question, data.next_step);
  } catch (error) { errorMessage.textContent = error.message; }
  finally { if (step < questions.length) { continueBtn.disabled = false; continueBtn.innerHTML = 'Continue <span aria-hidden="true">→</span>'; } }
});
renderQuestion(questions[0], 0);
