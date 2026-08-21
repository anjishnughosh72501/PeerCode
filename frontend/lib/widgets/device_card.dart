import 'package:flutter/material.dart';

import '../models/peer.dart';

class DeviceCard extends StatefulWidget {
  const DeviceCard({super.key, required this.host, required this.selected, required this.onTap});
  final DiscoveredHost host;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<DeviceCard> createState() => _DeviceCardState();
}

class _DeviceCardState extends State<DeviceCard> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: widget.onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          color: const Color(0xFF1C1C21),
          border: Border.all(color: widget.selected ? colors.primary : const Color(0xFF2A2A31)),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(widget.host.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(widget.host.filename, style: const TextStyle(color: Color(0xFF9A9AAA))),
                  const SizedBox(height: 4),
                  Text('${widget.host.ip}:${widget.host.port}', style: const TextStyle(color: Color(0xFF5C5C72), fontSize: 12)),
                ],
              ),
            ),
            FadeTransition(
              opacity: Tween<double>(begin: 0.35, end: 1).animate(_controller),
              child: Container(width: 10, height: 10, decoration: const BoxDecoration(color: Color(0xFF36D399), shape: BoxShape.circle)),
            ),
          ],
        ),
      ),
    );
  }
}
