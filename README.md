# code.teach

A dynamic, hands-on coding tutor that learns from your progress.
No lectures. No videos. Just tasks.

---

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
# add your GOOGLE_API_KEY to .env if you want live LLM responses
python main.py
```

## Deploying to Render

This repository is now set up for a straightforward Render deployment.

1. Push the repository to GitHub.
2. In Render, create a New Web Service.
3. Connect this repository and use the default settings.
4. Render will read [render.yaml](render.yaml) and start the app automatically.

No extra build steps are required beyond the standard Python environment.

Required environment variable:
- `GOOGLE_API_KEY` (needed for live AI responses; the app can still start without it)

The app exposes a health check at `/health`, so Render can verify startup automatically.

---

## Folder Structure

```
code_teach/
│
├── main.py                        ← entry point, wire UI + agent here (LAST)
├── config.py                      ← constants, model names, thresholds (DONE)
├── requirements.txt
│
├── app/
│   ├── models/
│   │   ├── llm.py                 ← STEP 1: LLM wrappers (ChatAnthropic)
│   │   └── embeddings.py          ← STEP 2: Embeddings model
│   │
│   ├── prompts/
│   │   ├── parsers.py             ← STEP 3: Pydantic models + Output parsers
│   │   └── templates.py           ← STEP 4: Prompt templates (ChatPromptTemplate)
│   │
│   ├── retrieval/
│   │   ├── loader.py              ← STEP 5: Document loaders + text splitters
│   │   ├── vector_store.py        ← STEP 6: Chroma vector stores (3 of them)
│   │   └── retrievers.py          ← STEP 7: Custom retrievers
│   │
│   ├── chains/
│   │   ├── planner_chain.py       ← STEP 8: LCEL chain (prompt | llm | parser)
│   │   └── difficulty_chain.py    ← STEP 9: RunnableLambda + logic chain
│   │
│   ├── memory/
│   │   └── session_memory.py      ← STEP 10: Cross-session persistence (JSON)
│   │
│   ├── agent/
│   │   ├── state.py               ← STEP 11: LangGraph TeachState (TypedDict)
│   │   ├── tools.py               ← STEP 12: @tool functions (run_code, search, etc.)
│   │   ├── nodes.py               ← STEP 13: Node functions (give_task, evaluate, etc.)
│   │   └── teacher_agent.py       ← STEP 14: StateGraph assembly + ReAct loop
│   │
│   └── ui/
│       └── terminal.py            ← STEP 15: Rich terminal UI
│
└── data/
    ├── sessions/                  ← session JSON files saved here
    ├── uploads/                   ← student PDFs/notes go here
    └── vectorstore/               ← Chroma DB persists here
```

---

## Build Order — Do This in Sequence

Each step teaches ONE LangChain concept.
Don't skip ahead. Each step depends on the previous.

### STEP 1 — `app/models/llm.py`
**Concept: LLM Wrappers & Chat Models**
- Install: `pip install langchain-anthropic`
- Import ChatAnthropic, create fast_llm and smart_llm
- Test: `python -c "from app.models.llm import fast_llm; print(fast_llm.invoke('hi').content)"`

### STEP 2 — `app/models/embeddings.py`
**Concept: Embeddings**
- Create the shared embeddings model
- Test: `python -c "from app.models.embeddings import get_embeddings; e = get_embeddings(); print(e.embed_query('hello'))"`

### STEP 3 — `app/prompts/parsers.py`
**Concept: Output Parsers + Structured Outputs**
- Fill in all Pydantic model fields (TeacherResponse, LessonPlan, etc.)
- Implement StudentProfile.update_after_task()
- Create PydanticOutputParser instances
- Test: parse a hardcoded JSON string into a TeacherResponse object

### STEP 4 — `app/prompts/templates.py`
**Concept: Prompt Templates (ChatPromptTemplate)**
- Build TEACH_PROMPT, FEEDBACK_PROMPT, PLANNER_PROMPT, DETOUR_PROMPT, SIGNAL_PROMPT
- Test: `print(TEACH_PROMPT.format(topic="Java", level="beginner", ...))`

### STEP 5 — `app/retrieval/loader.py`
**Concept: Document Loaders + Text Splitters**
- Implement load_pdf(), load_url(), load_text(), load_material()
- Test: load a PDF from data/uploads/ and print the first chunk

### STEP 6 — `app/retrieval/vector_store.py`
**Concept: Vector Stores (Chroma)**
- Start with FAISS (easier), then switch to Chroma
- Implement create_lesson_store(), get_task_store(), get_concept_store()
- Run populate_concept_store() once to seed it
- Test: create a store, add a doc, do similarity_search()

### STEP 7 — `app/retrieval/retrievers.py`
**Concept: Custom Retrievers**
- Implement ProgressAwareRetriever and MaterialRetriever
- Test: create a retriever, call .get_relevant_documents("inheritance")

### STEP 8 — `app/chains/planner_chain.py`
**Concept: LCEL Chains (the pipe operator)**
- Build: chain = PLANNER_PROMPT | smart_llm | lesson_plan_parser
- Implement run_planner()
- Test: run_planner("Java OOP", "beginner") → should return a LessonPlan object

### STEP 9 — `app/chains/difficulty_chain.py`
**Concept: RunnableLambda**
- Implement analyse_performance() and get_next_concept()
- Wrap as RunnableLambda
- Test with fake profile data

### STEP 10 — `app/memory/session_memory.py`
**Concept: Cross-session persistence**
- Implement save_session(), load_last_session()
- Test: save a fake SessionSummary, load it back

### STEP 11 — `app/agent/state.py`
**Concept: LangGraph State + Reducers**
- Fill in initial_state() defaults
- Add Annotated[List[BaseMessage], add_messages] to conversation_history
- Test: create initial_state() and print it

### STEP 12 — `app/agent/tools.py`
**Concept: Tools + Function Calling**
- Add @tool decorator to each function
- Implement run_code_snippet() first (most satisfying)
- Then search_student_notes(), get_task_history(), lookup_concept(), check_prerequisites()
- Test: run_code_snippet("print('hello')", "python") → should print "hello"

### STEP 13 — `app/agent/nodes.py`
**Concept: LangGraph Nodes**
- Implement nodes one at a time, test each before the next
- Start with give_task(), then evaluate_code(), then the rest
- Each node: read state → do work → return partial state update

### STEP 14 — `app/agent/teacher_agent.py`
**Concept: LangGraph StateGraph + ReAct**
- Implement build_graph() following the comments step by step
- Wire all nodes and edges
- Test with a single start_session() + submit_code() round trip

### STEP 15 — `app/ui/terminal.py`
**Concept: Rich terminal UI**
- Implement display functions using Rich panels, syntax highlighting, tables
- Test each display function individually

### FINAL — `main.py`
- Wire UI + agent together
- Run end-to-end: `python main.py`

---

## LangChain Concept Map

```
WHAT YOU LEARN          WHERE YOU USE IT
──────────────────────────────────────────────────────
LLM Wrappers        →   models/llm.py
Chat Models         →   models/llm.py
Embeddings          →   models/embeddings.py
Pydantic Parsers    →   prompts/parsers.py
Output Parsers      →   prompts/parsers.py
Prompt Templates    →   prompts/templates.py
Document Loaders    →   retrieval/loader.py
Text Splitters      →   retrieval/loader.py
Vector Stores       →   retrieval/vector_store.py
Retrievers          →   retrieval/retrievers.py
LCEL Chains (|)     →   chains/planner_chain.py
RunnableLambda      →   chains/difficulty_chain.py
Tools               →   agent/tools.py
Function Calling    →   agent/tools.py
LangGraph State     →   agent/state.py
LangGraph Nodes     →   agent/nodes.py
StateGraph          →   agent/teacher_agent.py
ReAct Pattern       →   agent/teacher_agent.py
Checkpointer Memory →   agent/teacher_agent.py
```

---

## Testing Each Step

Each file has a clear test you can run before moving on.
Never move to the next step until the current one works.

A working STEP N is more valuable than a skeleton STEP N+15.
