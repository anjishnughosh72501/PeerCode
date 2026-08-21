import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'editor_provider.g.dart';

class CursorPosition {
  const CursorPosition(
      {required this.line,
      required this.col,
      required this.color,
      required this.name});
  final int line;
  final int col;
  final String color;
  final String name;
}

class EditorState {
  const EditorState({
    required this.content,
    required this.lastSaved,
    required this.hasUnsavedChanges,
    required this.remoteCursors,
    required this.line,
    required this.col,
  });

  final String content;
  final DateTime? lastSaved;
  final bool hasUnsavedChanges;
  final Map<String, CursorPosition> remoteCursors;
  final int line;
  final int col;

  factory EditorState.initial() {
    return const EditorState(
      content: '',
      lastSaved: null,
      hasUnsavedChanges: false,
      remoteCursors: <String, CursorPosition>{},
      line: 1,
      col: 1,
    );
  }

  EditorState copyWith({
    String? content,
    DateTime? lastSaved,
    bool? hasUnsavedChanges,
    Map<String, CursorPosition>? remoteCursors,
    int? line,
    int? col,
  }) {
    return EditorState(
      content: content ?? this.content,
      lastSaved: lastSaved ?? this.lastSaved,
      hasUnsavedChanges: hasUnsavedChanges ?? this.hasUnsavedChanges,
      remoteCursors: remoteCursors ?? this.remoteCursors,
      line: line ?? this.line,
      col: col ?? this.col,
    );
  }
}

@riverpod
class EditorNotifier extends _$EditorNotifier {
  bool applyingRemote = false;

  @override
  EditorState build() => EditorState.initial();

  void applyRemoteText(String newContent) {
    applyingRemote = true;
    state = state.copyWith(content: newContent);
    applyingRemote = false;
  }

  Future<void> onLocalEdit(String oldText, String newText) async {
    if (applyingRemote || oldText == newText) return;
    state = state.copyWith(content: newText, hasUnsavedChanges: true);
  }

  Future<void> onLocalCursor(int line, int col) async {
    state = state.copyWith(line: line, col: col);
  }

  void updateRemoteCursor(String author, int line, int col, String color) {
    final cursors = Map<String, CursorPosition>.of(state.remoteCursors);
    cursors[author] =
        CursorPosition(line: line, col: col, color: color, name: author);
    state = state.copyWith(remoteCursors: cursors);
  }

  void removeRemoteCursor(String author) {
    final cursors = Map<String, CursorPosition>.of(state.remoteCursors)
      ..remove(author);
    state = state.copyWith(remoteCursors: cursors);
  }

  void markSaved(DateTime ts) {
    state = state.copyWith(lastSaved: ts, hasUnsavedChanges: false);
  }
}
