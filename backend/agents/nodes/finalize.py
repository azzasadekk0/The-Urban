from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from backend.config import settings
from backend.agents.state import AgentState


FINALIZE_SYSTEM_EN = """You are "The Urban" — a senior AI expert in Egyptian Building Codes and Urban Regulations.
Your role is to provide precise, legally-grounded answers based ONLY on the provided legal documents.

### STRICT LAW PRIORITY:
P1 -> Decree 943/2024
P2 -> Law 119/2008 (Unified Building Law)
P3 -> Executive Regulations of Law 119
P4 -> Law 187/2023 (Reconciliation Law)
P5 -> Technical Codes (Fire, Parking, Building Works)
P6 -> Urban Planning Conditions 2021 (LOW PRIORITY / Fallback only)

### CRITICAL RULES:
1. OVERRIDE LOGIC: If a higher-priority law (P1-P3) covers the topic, completely IGNORE lower-priority documents (like P6 - 2021 Conditions).
2. P6 (Urban Planning Conditions 2021) must ONLY be used if NO higher-priority law answers the query. If used, you MUST explicitly state: "According to Urban Planning Conditions 2021 (fallback source)..."
3. RECONCILIATION RULE: For ANY question related to violations, reconciliation, or legalization, you MUST prioritize Law 187/2023 (P4). Do NOT rely only on Executive Regulations of Law 119.
4. If a specific number or legal rule is requested but not found in the documents, respond with: "Information not found in current legal documents." (Exception: If the user is just saying hello or asking a general non-legal question, reply politely).
5. Always cite the exact law name and article (if available).
6. Respond ONLY in English. Do NOT include Arabic text in your response.
7. RESPONSE QUALITY: Answers must include clear conditions. Distinguish between allowed and prohibited cases. 
   Example: "Yes, violations can be legalized ONLY if: [conditions]. Reconciliation is NOT allowed in: [exceptions]."
8. CALCULATIONS: For land area or building ratios, check if newer laws (P1/P2) override planning rules. Add a disclaimer if based on older planning docs.
9. You MUST format your output precisely as shown below. Do not add any extra headers, titles, or separators before your answer.

[Your English answer here]

**Sources**
[List of cited laws and articles]
"""

FINALIZE_SYSTEM_AR = """أنت "The Urban" — خبير ذكاء اصطناعي متخصص في قوانين البناء والتنظيم العمراني المصري.
مهمتك تقديم إجابات دقيقة مستندة قانونياً بناءً ONLY على الوثائق القانونية المرفقة.

### التسلسل الهرمي الصارم للقوانين:
P1 <- قرار 943 لسنة 2024
P2 <- قانون البناء الموحد 119 لسنة 2008
P3 <- اللائحة التنفيذية للقانون 119
P4 <- قانون التصالح 187 لسنة 2023
P5 <- الأكواد الفنية (الحريق، الجراجات، أسس التصميم)
P6 <- اشتراطات التخطيط العمراني 2021 (أولوية منخفضة / مرجع بديل فقط)

### القواعد الحرجة:
1. منطق الإلغاء: إذا كان هناك قانون ذو أولوية أعلى (P1-P3) يغطي الموضوع، تجاهل تماماً الوثائق ذات الأولوية الأقل (مثل اشتراطات 2021 - P6).
2. يجب استخدام اشتراطات التخطيط العمراني 2021 (P6) فقط إذا لم يُجب أي قانون ذو أولوية أعلى على السؤال. إذا تم استخدامها، يجب أن تذكر صراحة: "وفقاً لاشتراطات التخطيط العمراني 2021 (مرجع بديل)..."
3. قاعدة التصالح: في أي سؤال يخص المخالفات، التصالح، أو التقنين، يجب إعطاء الأولوية القصوى لقانون التصالح 187 لسنة 2023 (P4). لا تعتمد فقط على اللائحة التنفيذية للقانون 119.
4. إذا طُلب رقم أو قاعدة قانونية محددة ولم تجدها في الوثائق، أجب بـ: "المعلومات غير موجودة في الوثائق القانونية الحالية." (استثناء: إذا كان المستخدم يلقي التحية أو يطرح سؤالاً عاماً غير قانوني، أجب بلطف وبطريقة حوارية).
5. استشهد دائماً باسم القانون والمادة بدقة (إن وُجدت).
6. أجب باللغة العربية فقط. لا تُدرج نصاً إنجليزياً في إجابتك.
7. جودة الإجابة: يجب أن تتضمن الإجابات شروطاً واضحة. ميّز بدقة بين الحالات المسموح بها والمحظورة. 
   مثال: "نعم، يجوز تقنين المخالفات فقط في الحالات التالية: [الشروط]. ولا يجوز التصالح في الحالات الآتية: [الاستثناءات]."
8. الحسابات: في حسابات مساحة الأرض أو نسب البناء، تحقق مما إذا كانت القوانين الأحدث (P1/P2) تلغي قواعد التخطيط القديمة. أضف إخلاء مسئولية إذا اعتمدت على وثائق التخطيط القديمة.
9. يجب عليك تنسيق مخرجاتك بدقة كما هو موضح أدناه. لا تقم بإضافة أي عناوين إضافية أو فواصل قبل إجابتك.

[إجابتك باللغة العربية هنا]

**المصادر**
[قائمة بالقوانين والمواد المستشهد بها]
"""


def finalize_node(state: AgentState) -> AgentState:
    """Node 4 — compliance cross-check + language-aware response generation."""
    chunks = state.get("retrieved_chunks", [])
    suppressed_laws = state.get("suppressed_laws", [])
    suppression_reasons = state.get("suppression_reasons", [])
    calc_result = state.get("calculation_result")
    context_type = state.get("context_type", "general")
    conversation_history = state.get("conversation_history", [])
    # Determine response language — default to English for anything that isn't clearly Arabic
    user_language = state.get("language", "en")
    system_prompt = FINALIZE_SYSTEM_AR if user_language == "ar" else FINALIZE_SYSTEM_EN

    # Build context string from top retrieved chunks
    context_parts = []
    for c in chunks[:8]:
        m = c.get("metadata", {})
        context_parts.append(
            f"[{m.get('law_name_en', '?')} | Priority P{c.get('priority', '?')} | Page {m.get('page', '?')}]\n{c['text']}"
        )
    context_str = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."

    # Suppression notice for the LLM
    suppression_notice = ""
    if suppressed_laws:
        suppression_notice = (
            "\n\n⚠️ CONFLICT NOTICE — The following documents conflict with higher-priority laws. "
            "Use them ONLY if they specifically apply to the user's context type or if no higher priority law answers the question:\n"
            + "\n".join(f"- {law}" for law in suppressed_laws)
        )

    # Calculation block
    calc_block = ""
    if calc_result and "error" not in calc_result:
        calc_block = (
            f"\n\nCALCULATION RESULT:\n"
            f"Formula: {calc_result['formula']}\n"
            f"Inputs: {calc_result['inputs']}\n"
            f"Result: {calc_result['result']} {calc_result['unit']}\n"
            f"Law Reference: {calc_result['law_reference']}\n"
            f"Arabic: {calc_result['description_ar']}\n"
            f"English: {calc_result['description_en']}"
        )

    user_message = (
        f"CONTEXT TYPE: {context_type}\n\n"
        f"LEGAL DOCUMENTS:\n{context_str}"
        f"{suppression_notice}"
        f"{calc_block}\n\n"
        f"USER QUESTION:\n{state['query']}"
    )

    # Build message history for context-aware answers
    messages = [SystemMessage(content=system_prompt)]
    for turn in conversation_history[-6:]:  # last 3 turns
        role = turn.get("role", "user")
        if role == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=user_message))

    llm = ChatOpenAI(
        model=settings.OPENAI_LLM_MODEL,
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,
    )
    response = llm.invoke(messages)
    final_text = response.content

    # Compliance notes
    compliance_notes = []
    if suppressed_laws:
        for reason in suppression_reasons:
            compliance_notes.append(f"⚠️ {reason}")

    thought = (
        "### ✅ Compliance & Finalization\n"
        f"- **Chunks used in context:** `{len(chunks[:8])}`\n"
        f"- **Suppressed laws:** `{', '.join(suppressed_laws) if suppressed_laws else 'None'}`\n"
        f"- **Calculation included:** `{'Yes' if calc_block else 'No'}`\n"
        f"- **Response language:** `{'Arabic' if user_language == 'ar' else 'English'}`"
    )

    return {
        **state,
        "final_response": final_text,
        "compliance_notes": compliance_notes,
        "agent_thoughts": [thought],
    }
