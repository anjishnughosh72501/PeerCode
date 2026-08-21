import 'package:flutter/material.dart';

class StatusBar extends StatelessWidget {
  const StatusBar({super.key, required this.line, required this.col, required this.hasUnsavedChanges, required this.lastSaved, required this.peerCount});

  final int line;
  final int col;
  final bool hasUnsavedChanges;
  final DateTime? lastSaved;
  final int peerCount;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 28,
      color: const Color(0xFF101013),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        children: <Widget>[
          SizedBox(width: 120, child: Text('Ln $line  Col $col', style: const TextStyle(fontSize: 12))),
          Expanded(child: Center(child: Text(_saveLabel(), style: const TextStyle(fontSize: 12, color: Color(0xFF9A9AAA))))),
          SizedBox(width: 120, child: Align(alignment: Alignment.centerRight, child: Text('$peerCount peers', style: const TextStyle(fontSize: 12)))),
        ],
      ),
    );
  }

  String _saveLabel() {
    if (hasUnsavedChanges) return 'Unsaved changes';
    if (lastSaved == null) return 'Not saved yet';
    final minutes = DateTime.now().difference(lastSaved!).inMinutes;
    return minutes <= 0 ? 'Saved just now' : 'Saved $minutes min ago';
  }
}
