import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/editor_provider.dart';

class EditorWidget extends ConsumerStatefulWidget {
  const EditorWidget({super.key});

  @override
  ConsumerState<EditorWidget> createState() => _EditorWidgetState();
}

class _EditorWidgetState extends ConsumerState<EditorWidget> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scroll = ScrollController();
  String _previous = '';
  bool _applyingRemote = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(editorNotifierProvider);
    ref.listen(editorNotifierProvider.select((s) => s.content), (_, next) {
      if (next == _controller.text) return;
      _applyingRemote = true;
      final selection = _controller.selection;
      _controller.text = next;
      _controller.selection = selection.copyWith(
        baseOffset: selection.baseOffset.clamp(0, next.length).toInt(),
        extentOffset: selection.extentOffset.clamp(0, next.length).toInt(),
      );
      _previous = next;
      _applyingRemote = false;
    });
    final lines = _controller.text.split('\n').length.clamp(1, 99999).toInt();
    return Stack(
      children: <Widget>[
        Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Container(
              width: 58,
              color: const Color(0xFF101013),
              child: ListView.builder(
                controller: _scroll,
                itemCount: lines,
                itemBuilder: (_, index) => SizedBox(
                  height: 20,
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: Padding(
                      padding: const EdgeInsets.only(right: 10),
                      child: Text('${index + 1}', style: const TextStyle(color: Color(0xFF5C5C72), fontSize: 13)),
                    ),
                  ),
                ),
              ),
            ),
            Expanded(
              child: TextField(
                controller: _controller,
                expands: true,
                maxLines: null,
                minLines: null,
                keyboardType: TextInputType.multiline,
                style: const TextStyle(fontFamily: 'JetBrains Mono', fontSize: 13, height: 1.54, color: Color(0xFFE8E8F0)),
                cursorColor: const Color(0xFF7C84FA),
                decoration: const InputDecoration(border: InputBorder.none, contentPadding: EdgeInsets.all(14)),
                inputFormatters: <TextInputFormatter>[FilteringTextInputFormatter.deny(RegExp(r'\u0000'))],
                onChanged: (_) => _emitCursor(),
                onTap: _emitCursor,
              ),
            ),
          ],
        ),
        Positioned(
          top: 8,
          right: 12,
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: state.remoteCursors.values
                .map((c) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(color: Color(int.parse('FF${c.color.substring(1)}', radix: 16)), borderRadius: BorderRadius.circular(6)),
                      child: Text('${c.name} ${c.line}:${c.col}', style: const TextStyle(fontSize: 10, color: Colors.white)),
                    ))
                .toList(),
          ),
        ),
      ],
    );
  }

  void _onTextChanged() {
    if (_applyingRemote) return;
    final next = _controller.text;
    final old = _previous;
    _previous = next;
    ref.read(editorNotifierProvider.notifier).onLocalEdit(old, next);
  }

  void _emitCursor() {
    final pos = _controller.selection.baseOffset.clamp(0, _controller.text.length).toInt();
    final before = _controller.text.substring(0, pos);
    final line = '\n'.allMatches(before).length + 1;
    final lastNewline = before.lastIndexOf('\n');
    final col = pos - lastNewline;
    ref.read(editorNotifierProvider.notifier).onLocalCursor(line, col);
  }
}
