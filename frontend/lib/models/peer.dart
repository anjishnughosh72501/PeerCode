import 'package:flutter/material.dart';

Color colorFromHex(String hex) {
  final cleaned = hex.replaceFirst('#', '');
  return Color(int.parse('FF$cleaned', radix: 16));
}

String colorToHex(Color color) {
  final value = color.toARGB32() & 0xFFFFFF;
  return '#${value.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}

class Peer {
  const Peer({required this.name, required this.color, required this.isHost});

  final String name;
  final Color color;
  final bool isHost;

  factory Peer.fromJson(Map<String, Object?> json) {
    return Peer(
      name: json['name'] as String? ?? 'Unknown',
      color: colorFromHex(json['color'] as String? ?? '#7C84FA'),
      isHost: json['isHost'] as bool? ?? false,
    );
  }
}

class DiscoveredHost {
  const DiscoveredHost({required this.name, required this.ip, required this.port, required this.filename});

  final String name;
  final String ip;
  final int port;
  final String filename;

  factory DiscoveredHost.fromJson(Map<String, Object?> json) {
    return DiscoveredHost(
      name: json['name'] as String? ?? 'Unknown',
      ip: json['ip'] as String? ?? '',
      port: json['port'] as int? ?? 8765,
      filename: json['filename'] as String? ?? 'Untitled',
    );
  }
}
