import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../services/backend_launcher.dart';

class ErrorScreen extends StatelessWidget {
  const ErrorScreen({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0F),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.error_outline,
                  size: 48, color: Color(0xFFC45C5C)),
              const SizedBox(height: 16),
              Text(
                'PeerCode failed to start',
                style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: const Color(0xFFE8E8F0)),
              ),
              const SizedBox(height: 8),
              Text(
                'The backend process could not be launched.',
                style: GoogleFonts.inter(
                    fontSize: 13, color: const Color(0xFF5C5C72)),
              ),
              const SizedBox(height: 16),
              Container(
                width: 480,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF141417),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF2C2C32)),
                ),
                child: SelectableText(
                  message,
                  style: GoogleFonts.jetBrainsMono(
                      fontSize: 11, color: const Color(0xFFA0A0B0)),
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Color(0xFF7C84FA)),
                      foregroundColor: const Color(0xFF7C84FA),
                    ),
                    onPressed: () async {
                      await BackendLauncher.dispose();
                      onRetry();
                    },
                    child: const Text('Retry'),
                  ),
                  const SizedBox(width: 12),
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFC45C5C)),
                    onPressed: () => exit(0),
                    child: const Text('Quit'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
