export type TextDirection = 'rtl' | 'ltr'

export interface DirectionSegment {
    text: string
    dir: TextDirection
}

function detectDirection(text: string): TextDirection {
    const arabicCount = (text.match(/[\u0600-\u06FF]/g) || []).length
    const latinCount = (text.match(/[A-Za-z]/g) || []).length
    if (arabicCount > latinCount) {
        return 'rtl'
    }
    return 'ltr'
}

export function splitTextByDirection(text: string): DirectionSegment[] {
    const value = (text || '').replace(/\r\n/g, '\n').trim()
    if (!value) {
        return []
    }

    const segments: DirectionSegment[] = []

    for (const rawLine of value.split('\n')) {
        const line = rawLine.trim()
        if (!line) {
            continue
        }
        // Keep mixed-script content in one segment per line to avoid
        // breaking Arabic sentences when English terms appear inline.
        const fallbackDir = detectDirection(line)
        segments.push({ text: line, dir: fallbackDir })
    }

    return segments.length ? segments : [{ text: value, dir: detectDirection(value) }]
}
