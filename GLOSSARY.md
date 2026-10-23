# Voice Journal

A local-first journal that turns spoken reflection into structured, searchable writing. "Nightly" describes how people are expected to use it, not a rule the model enforces: the app never requires exactly one piece of writing per day.

## Language

### The writing

**Entry**:
A single saved piece of journal writing, together with everything derived from the speech that produced it. The central thing the app stores; there may be any number per day, at any hour.
_Avoid_: Journal, Night, Post, Note, Log

**Draft**:
A processed Entry that the author has not yet committed. It exists only while the author is reviewing it and is lost if they abandon the session.
_Avoid_: Pending entry, Unsaved entry, Temp entry

**Author**:
The person whose journal this is. There is exactly one per installation.
_Avoid_: User, Account, Owner

**Journal Day**:
The day an Entry is counted against, which ends in the small hours rather than at midnight. An Entry recorded shortly after midnight belongs to the Journal Day that just ended, matching how people talk about the night they are writing about.
_Avoid_: Date, Calendar day, Night

**Prompt**:
An optional question shown to the Author before recording to guide what they say. When used, it is kept with the resulting Entry as context, but it is never part of the Transcript.
_Avoid_: Question, Guide, Reflection prompt

**Weekly Review**:
A clearly labeled interpretation by the model spanning the Entries in one week of Journal Days, Monday through Sunday. It is not an Entry and does not count towards a Streak.
_Avoid_: Weekly summary, Reflection, Digest

**Streak**:
The number of consecutive Journal Days up to and including the current one that contain at least one Entry. The current Journal Day counts towards the Streak until it ends unwritten, so a Streak is never shortened merely by the day being young.
_Avoid_: Run, Chain, Consistency

### The speech

**Recording**:
The captured audio of the Author speaking. It is transient: it exists only long enough to be transcribed and is then discarded.
_Avoid_: Audio, Clip, Take, Blob

**Transcript**:
The verbatim text of what the Author said, as heard by the transcriber. Never edited and never regenerated, because the Recording it came from no longer exists.
_Avoid_: Raw text, Transcription, STT output

### What the model derives

**Summary**:
A condensed, readable rendering of the Transcript in the Author's own voice. Distinct from the Transcript: it is interpretation, not record.
_Avoid_: Description, Abstract, Body

**Title**:
A short phrase naming what an Entry is about.
_Avoid_: Heading, Name, Subject

**Mood**:
The emotional tone of an Entry, chosen from a fixed, closed set of named tones. The set is defined by the app and does not vary between installations.
_Avoid_: Tone, Emotion, Sentiment, Feeling

**Valence**:
Whether a Mood is negative, neutral, or positive. The property that makes Moods comparable to one another and therefore plottable over time.
_Avoid_: Polarity, Score, Rating

**Tag**:
A short lowercase topic label attached to an Entry. Tags are not drawn from a fixed list, but the Author's existing Tags are preferred over new ones describing the same thing.
_Avoid_: Topic, Category, Label, Keyword

**Action Item**:
A task or commitment the Author mentioned aloud. Recorded as stated; the app does not track whether it was done.
_Avoid_: Todo, Task, Commitment, Reminder
