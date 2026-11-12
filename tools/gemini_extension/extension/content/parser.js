/**
 * Cognitive Response Parser for Gemini
 * Resilient JSON extraction and 6-skill taxonomy rubric validation
 */

const CognitiveParser = {
  REQUIRED_SKILLS: [
    'attention',
    'working_memory',
    'logical_reasoning',
    'language_processing',
    'critical_thinking',
    'metacognition',
  ],

  cleanRawText(text) {
    if (!text) return '';
    let cleaned = text.trim();
    cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '');
    cleaned = cleaned.replace(/<thought>[\s\S]*?<\/thought>/gi, '');
    return cleaned.trim();
  },

  extractJsonString(rawText) {
    const cleaned = this.cleanRawText(rawText);

    // 1. Search for markdown code blocks containing 'attention'
    const codeBlocks = Array.from(cleaned.matchAll(/```(?:json)?\s*([\s\S]*?)\s*```/gi));
    for (const match of codeBlocks) {
      if (match[1] && (match[1].includes('attention') || match[1].includes('working_memory'))) {
        return match[1].trim();
      }
    }

    // 2. Search for { ... } block containing 'attention'
    const firstBrace = cleaned.indexOf('{');
    const lastBrace = cleaned.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
      const candidate = cleaned.substring(firstBrace, lastBrace + 1).trim();
      if (candidate.includes('attention') || candidate.includes('working_memory')) {
        return candidate;
      }
    }

    // 3. Fallback: Any markdown code block
    if (codeBlocks.length > 0 && codeBlocks[0][1]) {
      return codeBlocks[0][1].trim();
    }

    // 4. Fallback: Outermost curly braces
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
      return cleaned.substring(firstBrace, lastBrace + 1).trim();
    }

    return cleaned;
  },

  parseAndValidate(rawText, expectedQuestionId = null) {
    const jsonStr = this.extractJsonString(rawText);
    if (!jsonStr) {
      throw new Error("No JSON block found in Gemini response.");
    }

    let parsed;
    try {
      parsed = JSON.parse(jsonStr);
    } catch (err) {
      // Fallback: sanitize unescaped control characters/newlines inside string literals
      try {
        const sanitized = jsonStr.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/gs, (match) => {
          return match.replace(/\r?\n/g, '\\n').replace(/\t/g, '\\t');
        });
        parsed = JSON.parse(sanitized);
      } catch (_) {
        throw new Error(`Invalid JSON returned: ${err.message}. Raw snippet: ${jsonStr.slice(0, 100)}`);
      }
    }

    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      throw new Error("Parsed JSON is not an object.");
    }

    // Anti-stale check: If question_id is provided in the JSON, ensure it matches
    if ('question_id' in parsed && parsed.question_id !== null && parsed.question_id !== undefined) {
      const parsedId = parseInt(parsed.question_id, 10);
      if (!isNaN(parsedId) && expectedQuestionId !== null && parsedId !== expectedQuestionId) {
        throw new Error(
          `Stale output detected: response specifies question_id #${parsedId}, but currently expecting #${expectedQuestionId}`
        );
      }
    }

    // Validate 6 skills
    const validatedScores = {};
    for (const skill of this.REQUIRED_SKILLS) {
      if (!(skill in parsed)) {
        throw new Error(`Missing required cognitive skill: '${skill}'`);
      }
      let val = parsed[skill];
      if (typeof val === 'string') {
        val = parseInt(val, 10);
      } else if (typeof val === 'number') {
        val = Math.round(val);
      } else {
        throw new Error(`Invalid score type for '${skill}': ${typeof val}`);
      }

      if (isNaN(val) || val < 0 || val > 3) {
        throw new Error(`Score for '${skill}' must be an integer between 0 and 3, got: ${val}`);
      }
      validatedScores[skill] = val;
    }

    // Validate confidence
    let confidence = 0.95;
    if ('confidence' in parsed) {
      const conf = parseFloat(parsed.confidence);
      if (!isNaN(conf) && conf >= 0.0 && conf <= 1.0) {
        confidence = conf;
      }
    }

    // Extract rationale
    const rationale =
      parsed.short_rationale ||
      parsed.rationale ||
      parsed.explanation ||
      parsed.reasoning ||
      "Grounded assessment of question cognitive demands.";

    return {
      question_id: expectedQuestionId !== null ? expectedQuestionId : (parsed.question_id ?? 0),
      scores: validatedScores,
      confidence,
      short_rationale: String(rationale).trim(),
    };
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CognitiveParser;
}
