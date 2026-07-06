// App State Management
const state = {
  currentScreen: 'landing',
  topic: null,
  level: null,
  assessment: [],
  sessionId: `session_${Date.now()}`,
  taskCount: 0,
  totalTasks: 5,
  lastResponse: null,
  topicExplanation: null
};

// Assessment Questions
const assessmentQuestions = {
  'Python Variables': [
    {
      question: 'What is a variable?',
      options: [
        'A container for storing a value',
        'A type of loop',
        'A function parameter only',
        'A syntax error'
      ]
    },
    {
      question: 'How do you create a variable in Python?',
      options: [
        'var x = 5',
        'x = 5',
        'let x = 5',
        'declare x = 5'
      ]
    }
  ],
  'Python Functions': [
    {
      question: 'What is a function?',
      options: [
        'A reusable block of code',
        'A variable type',
        'A loop statement',
        'A comment'
      ]
    },
    {
      question: 'How do you define a function in Python?',
      options: [
        'function myFunc() {}',
        'def myFunc():',
        'func myFunc:',
        'define myFunc:'
      ]
    }
  ]
};

const topicExplanations = {
  'Python Variables': 'Variables are containers for storing data values. In Python, you create a variable by assigning a value to a name. Variables can hold different types of data: strings, numbers, lists, and more.',
  'Python Functions': 'Functions are blocks of reusable code. They help organize your code, reduce repetition, and make programs easier to maintain. You define a function with def and call it by using its name with parentheses.',
  'Python Loops': 'Loops allow you to repeat a block of code multiple times. Python has for loops (for iterating over sequences) and while loops (for conditional repetition).',
  'Python Dictionaries': 'Dictionaries store data as key-value pairs. They are unordered, mutable collections that allow you to quickly look up values using keys.',
  'Python Lists': 'Lists are ordered collections of items. They can contain any type of data and support indexing, slicing, and various manipulation methods.',
  'Java Variables': 'Java variables must be declared with a type (int, String, boolean, etc.) before use. This type-safety helps catch errors early.',
  'Java Functions': 'Methods in Java are functions that belong to classes. They must specify return types and parameter types explicitly.'
};

// Screen Navigation
function showScreen(screenName) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${screenName}`).classList.add('active');
  state.currentScreen = screenName;
}

// Event Listeners - Landing Page
document.getElementById('btn-start-onboarding').addEventListener('click', () => {
  showScreen('select');
});

// Event Listeners - Topic & Level Selection
document.getElementById('btn-back-landing').addEventListener('click', () => {
  showScreen('landing');
});

document.querySelectorAll('.level-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.level-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.level = btn.dataset.level;
  });
});

document.getElementById('btn-next-assessment').addEventListener('click', () => {
  state.topic = document.getElementById('topic').value;
  if (!state.topic || !state.level) {
    alert('Please select both a topic and a level.');
    return;
  }
  populateAssessment().then(() => showScreen('assessment'));
});

// Assessment Population
async function populateAssessment() {
  const container = document.getElementById('assessment-questions');
  container.innerHTML = '';

  try {
    // Build conversation context from displayed messages to bias the quiz
    const convoNodes = Array.from(document.querySelectorAll('.message .message-content')) || [];
    const conversation = convoNodes.map(n => n.textContent.trim()).join('\n');

    const resp = await fetch('/api/session/assessment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: state.topic, level: state.level || 'beginner', conversation: conversation })
    });
    const data = await resp.json();
    const questions = (data && data.questions) || [];
    state.assessment = questions.map((q) => ({
      ...q,
      selected_option: null,
      correct_option: q.correct_option ?? null,
    }));

    state.assessment.forEach((q, idx) => {
      const questionEl = document.createElement('div');
      questionEl.className = 'assessment-question';
      questionEl.innerHTML = `
        <p><strong>Q${idx + 1}:</strong> ${q.question}</p>
        <div class="assessment-options">
          ${q.options.map((opt, optIdx) => `
            <button class="assessment-option" data-question="${idx}" data-option="${optIdx}">
              ${opt}
            </button>
          `).join('')}
        </div>
      `;
      container.appendChild(questionEl);
    });

    // Add event listeners to assessment options
    container.querySelectorAll('.assessment-option').forEach(btn => {
      btn.addEventListener('click', () => {
        const questionIndex = Number(btn.dataset.question);
        const optionIndex = Number(btn.dataset.option);
        const parent = btn.parentElement;
        parent.querySelectorAll('button').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        if (state.assessment[questionIndex]) {
          state.assessment[questionIndex].selected_option = optionIndex;
        }
      });
    });
  } catch (err) {
    console.error('Assessment fetch failed', err);
    // Fallback to a simple question
    container.innerHTML = '<div class="assessment-question"><p>No assessment available — press Start to continue.</p></div>';
  }
}

// Event Listeners - Assessment
document.getElementById('btn-back-select').addEventListener('click', () => {
  showScreen('select');
});

document.getElementById('btn-start-session').addEventListener('click', async () => {
  await initializeSession();
  showScreen('session');
});

// Initialize Session
async function initializeSession() {
  try {
    const response = await fetch('/api/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: state.topic,
        level: state.level,
        assessment: state.assessment
      })
    });
    
    const data = await response.json();
    state.lastResponse = data;
    state.taskCount = 1;
    
    // Update session header
    const displayTopic = (state.topic || '').trim();
    document.getElementById('topic-tag').textContent = displayTopic;
    document.getElementById('level-tag').textContent = state.level.charAt(0).toUpperCase() + state.level.slice(1);
    document.getElementById('task-counter').textContent = `Task ${state.taskCount} of ${state.totalTasks}`;
    
    // Set topic explanation
    if (topicExplanations[displayTopic]) {
      state.topicExplanation = topicExplanations[displayTopic];
    } else {
      state.topicExplanation = `I'll create a short learning path and practice tasks for "${displayTopic}" to get you started.`;
    }
    document.getElementById('topic-explanation').innerHTML = `
      <h3>${displayTopic}</h3>
      <p>${state.topicExplanation}</p>
    `;
    
    // Clear messages
    document.getElementById('messages').innerHTML = '';
    
    // Display initial message and task
    if (data.message) {
      addMessage(data.message, 'teacher');
    }
    if (data.task) {
      addMessage(`Task: ${data.task}`, 'teacher');
    }
    if (data.starter_code) {
      document.getElementById('code').value = data.starter_code;
    }
  } catch (error) {
    console.error('Failed to start session:', error);
    addMessage('Failed to start session. Please try again.', 'teacher');
  }
}

// Add Message Function
function addMessage(text, role = 'teacher') {
  const messagesDiv = document.getElementById('messages');
  const messageEl = document.createElement('div');
  messageEl.className = `message ${role}`;
  
  const labelEl = document.createElement('div');
  labelEl.className = 'message-label';
  labelEl.textContent = role === 'teacher' ? 'Teacher' : 'You';
  
  const contentEl = document.createElement('div');
  contentEl.className = 'message-content';
  contentEl.textContent = text;
  
  messageEl.appendChild(labelEl);
  messageEl.appendChild(contentEl);
  
  messagesDiv.appendChild(messageEl);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Event Listeners - Session
document.getElementById('submit-btn').addEventListener('click', async () => {
  const code = document.getElementById('code').value.trim();
  if (!code) {
    alert('Please write some code first.');
    return;
  }
  
  document.getElementById('submit-btn').disabled = true;
  addMessage(code, 'student');
  
  try {
    const response = await fetch('/api/session/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    
    const data = await response.json();
    state.lastResponse = data;
    
    if (data.message) {
      addMessage(data.message, 'teacher');
    }
    if (data.task) {
      addMessage(`Next Task: ${data.task}`, 'teacher');
      state.taskCount++;
      document.getElementById('task-counter').textContent = `Task ${state.taskCount} of ${state.totalTasks}`;
    }
    if (data.starter_code) {
      document.getElementById('code').value = data.starter_code;
    }
  } catch (error) {
    console.error('Failed to submit code:', error);
    addMessage('Failed to submit. Please try again.', 'teacher');
  }
  
  document.getElementById('submit-btn').disabled = false;
});

// Signal Buttons
document.querySelectorAll('.signal-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const signal = btn.dataset.signal;
    addMessage(`Need help: ${signal.replace(/_/g, ' ')}`, 'student');
    
    try {
      const response = await fetch('/api/session/signal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal })
      });
      
      const data = await response.json();
      if (data.message) {
        addMessage(data.message, 'teacher');
      }
    } catch (error) {
      console.error('Failed to send signal:', error);
      addMessage('Could not process your request. Please try again.', 'teacher');
    }
  });
});

document.getElementById('btn-end-session').addEventListener('click', async () => {
  try {
    const response = await fetch('/api/session/end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    displaySummary(data);
    showScreen('summary');
  } catch (error) {
    console.error('Failed to end session:', error);
    addMessage('Failed to end session. Please try again.', 'teacher');
  }
});

// Summary Display
function displaySummary(summary) {
  const container = document.getElementById('summary-content');
  container.innerHTML = `
    <div class="summary-stat">
      <div class="label">Topic</div>
      <div class="value">${summary.topic || state.topic}</div>
    </div>
    <div class="summary-stat">
      <div class="label">Tasks Completed</div>
      <div class="value">${state.taskCount}</div>
    </div>
    <div class="summary-stat">
      <div class="label">Difficulty Level</div>
      <div class="value">${state.level.charAt(0).toUpperCase() + state.level.slice(1)}</div>
    </div>
    <div class="summary-stat">
      <div class="label">Next Steps</div>
      <div class="value">${summary.next_focus || 'Great job! Keep practicing.'}</div>
    </div>
  `;
}

// New Session
document.getElementById('btn-new-session').addEventListener('click', () => {
  state.topic = null;
  state.level = null;
  state.assessment = [];
  state.taskCount = 0;
  state.lastResponse = null;
  document.getElementById('code').value = '';
  showScreen('landing');
});

