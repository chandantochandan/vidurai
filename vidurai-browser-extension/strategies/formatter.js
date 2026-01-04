/**
 * Context Formatter - Clean, AI-friendly context
 * Philosophy: Signal, not noise. Relevant, not overwhelming.
 */

class ContextFormatter {
    /**
     * Format context for AI consumption
     * Filters noise, highlights signal
     */
    static formatForAI(rawContext, platform) {
        // Extract only relevant information
        const filtered = this.filterNoise(rawContext);

        // Format based on AI platform preferences
        switch (platform) {
            case 'ChatGPT':
                return this.formatForChatGPT(filtered);
            case 'Claude.ai':
                return this.formatForClaude(filtered);
            case 'Gemini':
                return this.formatForGemini(filtered);
            default:
                return this.formatUniversal(filtered);
        }
    }

    /**
     * Filter out noise - keep only signal
     * विस्मृति भी विद्या है - Forgetting too is knowledge
     */
    static filterNoise(context) {
        // Remove:
        // - Repetitive npm install outputs
        // - Successful test runs (keep only failures)
        // - Unchanged file notifications

        return {
            project: context.project,
            recentChanges: context.changes_detected > 0 ? 'Active development' : 'Stable',
            filesMonitored: context.files_watched,
            lastActivity: this.formatTime(context.last_activity)
        };
    }

    static formatForChatGPT(context) {
        return `[Context: ${context.project} | ${context.filesMonitored} files | ${context.recentChanges}]`;
    }

    static formatForClaude(context) {
        return `<context project="${context.project}" files="${context.filesMonitored}" status="${context.recentChanges}" />`;
    }

    static formatForGemini(context) {
        return `# Project Context\nName: ${context.project}\nFiles: ${context.filesMonitored}\nStatus: ${context.recentChanges}`;
    }

    static formatUniversal(context) {
        return `[VIDURAI] ${context.project} - ${context.filesMonitored} files - ${context.recentChanges}`;
    }

    static formatTime(timestamp) {
        if (!timestamp) return 'N/A';
        // Convert to relative time
        const now = new Date();
        const then = new Date(timestamp);
        const diff = Math.floor((now - then) / 1000);

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }
}
