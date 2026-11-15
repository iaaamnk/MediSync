import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../models/report_model.dart';
import '../services/api_service.dart';

class PatientPortalScreen extends StatefulWidget {
  final Function(MedicalReport)? onReportLoaded;

  const PatientPortalScreen({Key? key, this.onReportLoaded}) : super(key: key);

  @override
  State<PatientPortalScreen> createState() => _PatientPortalScreenState();
}

class _PatientPortalScreenState extends State<PatientPortalScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  MedicalReport? _currentReport;
  bool _isLoading = false;
  List<Doctor> _doctors = [];
  List<Appointment> _appointments = [];

  // Appointment Form Controllers
  final _nameCtrl = TextEditingController(text: "Sarah Connor");
  final _phoneCtrl = TextEditingController(text: "+1 555-0192");
  final _reasonCtrl = TextEditingController(text: "Routine lab review");
  final _tokenCtrl = TextEditingController();
  String? _selectedDoctorId;
  String _selectedDate = "2026-11-05";
  String _selectedTime = "10:00 AM";

  // Voice Query
  final _voiceQueryCtrl = TextEditingController();
  String? _voiceResponse;
  bool _isVoiceLoading = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadInitialData();
  }

  Future<void> _loadInitialData() async {
    final docs = await ApiService.getDoctors();
    final appts = await ApiService.getAppointments();
    setState(() {
      _doctors = docs;
      _appointments = appts;
      if (docs.isNotEmpty) _selectedDoctorId = docs.first.id;
    });
  }

  Future<void> _fetchSample(String type) async {
    setState(() => _isLoading = true);
    final report = await ApiService.loadSampleReport(type);
    setState(() {
      _isLoading = false;
      _currentReport = report;
      if (report != null) {
        _tokenCtrl.text = report.token;
        if (widget.onReportLoaded != null) widget.onReportLoaded!(report);
      }
    });
  }

  Future<void> _bookAppointment() async {
    if (_selectedDoctorId == null) return;
    final success = await ApiService.bookAppointment(
      patientName: _nameCtrl.text,
      patientPhone: _phoneCtrl.text,
      doctorId: _selectedDoctorId!,
      date: _selectedDate,
      time: _selectedTime,
      reason: _reasonCtrl.text,
      reportToken: _tokenCtrl.text.isNotEmpty ? _tokenCtrl.text : null,
    );

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Appointment booked successfully!"), backgroundColor: Colors.teal),
      );
      final appts = await ApiService.getAppointments();
      setState(() {
        _appointments = appts;
      });
      _tabController.animateTo(2); // Jump to My Appointments
    }
  }

  Future<void> _askVoice(String text) async {
    setState(() {
      _isVoiceLoading = true;
      _voiceResponse = null;
    });
    final res = await ApiService.sendChatMessage(
      message: text,
      reportId: _currentReport?.id,
    );
    setState(() {
      _isVoiceLoading = false;
      _voiceResponse = res?['reply'] ?? "Could not generate response.";
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: const Color(0xFF0D9488),
            unselectedLabelColor: Colors.grey.shade600,
            indicatorColor: const Color(0xFF0D9488),
            indicatorWeight: 3,
            tabs: const [
              Tab(icon: Icon(Icons.document_scanner), text: "Analyzer"),
              Tab(icon: Icon(Icons.calendar_month), text: "Book"),
              Tab(icon: Icon(Icons.list_alt), text: "Appointments"),
              Tab(icon: Icon(Icons.mic), text: "Voice Assistant"),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [
              _buildAnalyzerTab(),
              _buildBookTab(),
              _buildAppointmentsTab(),
              _buildVoiceTab(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAnalyzerTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Sample Buttons
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            elevation: 1,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Quick Test with Clinical Samples", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  const Text("Select a sample lab test to evaluate Gemini's non-diagnostic medical report explainer:", style: TextStyle(color: Colors.black54, fontSize: 13)),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ActionChip(
                        avatar: const Text("🩸"),
                        label: const Text("CBC Blood Count"),
                        onPressed: () => _fetchSample("cbc"),
                        backgroundColor: const Color(0xFFCCFBF1),
                      ),
                      ActionChip(
                        avatar: const Text("🫀"),
                        label: const Text("Lipid Profile"),
                        onPressed: () => _fetchSample("lipid"),
                        backgroundColor: const Color(0xFFCCFBF1),
                      ),
                      ActionChip(
                        avatar: const Text("🧪"),
                        label: const Text("Metabolic Glucose"),
                        onPressed: () => _fetchSample("metabolic"),
                        backgroundColor: const Color(0xFFCCFBF1),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Column(
                  children: [
                    CircularProgressIndicator(color: Color(0xFF0D9488)),
                    SizedBox(height: 12),
                    Text("Gemini AI analyzing laboratory indicators...", style: TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ),

          if (!_isLoading && _currentReport != null) ...[
            // MANDATORY MEDICAL SAFETY DISCLAIMER
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                border: const Border(left: BorderSide(color: Color(0xFFF59E0B), width: 4)),
                borderRadius: BorderRadius.circular(8),
              ),
              padding: const EdgeInsets.all(12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Color(0xFFF59E0B), size: 24),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text("Medical Safety Disclaimer", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF92400E))),
                        const SizedBox(height: 4),
                        Text(_currentReport!.disclaimer, style: const TextStyle(fontSize: 12, color: Color(0xFF78350F))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // QR Pass Card
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              color: const Color(0xFFF0FDFA),
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const Text("Doctor QR Access Pass", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF0F766E))),
                    const SizedBox(height: 4),
                    const Text("Doctor scans this code to access full record & attach clinical consultation notes.", style: TextStyle(fontSize: 12, color: Colors.black54), textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    Container(
                      color: Colors.white,
                      padding: const EdgeInsets.all(8),
                      child: QrImageView(
                        data: "http://127.0.0.1:8000/?portal=doctor&token=${_currentReport!.token}",
                        version: QrVersions.auto,
                        size: 160.0,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(color: const Color(0xFFCCFBF1), borderRadius: BorderRadius.circular(6)),
                      child: Text("TOKEN: ${_currentReport!.token}", style: const TextStyle(fontWeight: FontWeight.bold, fontFamily: 'monospace', color: Color(0xFF0F766E))),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Parameter Table Cards
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_currentReport!.reportTitle, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                    const SizedBox(height: 4),
                    Text(_currentReport!.summaryOverview, style: const TextStyle(color: Colors.black87, fontSize: 13)),
                    const Divider(height: 24),
                    const Text("Laboratory Indicators & Reference Norms:", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    const SizedBox(height: 8),
                    ..._currentReport!.parameters.map((p) {
                      Color badgeColor = Colors.green.shade100;
                      Color textColor = Colors.green.shade800;
                      if (p.status.toLowerCase().contains("high")) {
                        badgeColor = Colors.red.shade100;
                        textColor = Colors.red.shade800;
                      } else if (p.status.toLowerCase().contains("low")) {
                        badgeColor = Colors.blue.shade100;
                        textColor = Colors.blue.shade800;
                      }

                      return Container(
                        margin: const EdgeInsets.symmetric(vertical: 4),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(color: Colors.grey.shade50, borderRadius: BorderRadius.circular(8)),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              flex: 3,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(p.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                  Text(p.explanation, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                                ],
                              ),
                            ),
                            Expanded(
                              flex: 2,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Text(p.value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                                  Text("Ref: ${p.referenceRange}", style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                                  const SizedBox(height: 2),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(color: badgeColor, borderRadius: BorderRadius.circular(4)),
                                    child: Text(p.status, style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10)),
                                  )
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Questions for doctor
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 1,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text("🩺 Questions for Your Doctor", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                    const SizedBox(height: 8),
                    ..._currentReport!.questionsForDoctor.map((q) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text("• ", style: TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.bold)),
                          Expanded(child: Text(q, style: const TextStyle(fontSize: 13))),
                        ],
                      ),
                    )),
                  ],
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }

  Widget _buildBookTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        elevation: 1,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("Schedule a Doctor Consultation", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 16),
              const Text("Select Specialist Physician", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
              const SizedBox(height: 8),
              ..._doctors.map((doc) => RadioListTile<String>(
                value: doc.id,
                groupValue: _selectedDoctorId,
                onChanged: (val) => setState(() => _selectedDoctorId = val),
                title: Text(doc.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                subtitle: Text("${doc.specialty} • ${doc.hospital}"),
                secondary: Text(doc.avatar, style: const TextStyle(fontSize: 24)),
              )),
              const Divider(height: 24),
              TextField(
                controller: _nameCtrl,
                decoration: const InputDecoration(labelText: "Patient Name", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _phoneCtrl,
                decoration: const InputDecoration(labelText: "Contact Phone", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _tokenCtrl,
                decoration: const InputDecoration(labelText: "Attached Report Token (Optional)", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _reasonCtrl,
                decoration: const InputDecoration(labelText: "Reason for Consultation", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0D9488),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: _bookAppointment,
                child: const Center(child: Text("Confirm Appointment", style: TextStyle(fontWeight: FontWeight.bold))),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAppointmentsTab() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _appointments.length,
      itemBuilder: (context, i) {
        final a = _appointments[i];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          child: ListTile(
            leading: const CircleAvatar(backgroundColor: Color(0xFFCCFBF1), child: Icon(Icons.medical_services, color: Color(0xFF0D9488))),
            title: Text(a.doctorName, style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Text("${a.doctorSpecialty}\n📅 ${a.date} at ${a.time} • Patient: ${a.patientName}"),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(color: Colors.teal.shade50, borderRadius: BorderRadius.circular(6)),
              child: Text(a.status, style: const TextStyle(color: Color(0xFF0D9488), fontWeight: FontWeight.bold, fontSize: 11)),
            ),
          ),
        );
      },
    );
  }

  Widget _buildVoiceTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const SizedBox(height: 20),
          GestureDetector(
            onTap: () => _askVoice("Explain my latest laboratory findings in simple non-diagnostic terms."),
            child: CircleAvatar(
              radius: 40,
              backgroundColor: const Color(0xFF0D9488),
              child: const Icon(Icons.mic, size: 40, color: Colors.white),
            ),
          ),
          const SizedBox(height: 12),
          const Text("Tap Microphone or type below", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: [
              ActionChip(label: const Text("What is Hemoglobin?"), onPressed: () => _askVoice("What does hemoglobin measure?")),
              ActionChip(label: const Text("Why fasting glucose?"), onPressed: () => _askVoice("Why is fasting glucose important?")),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _voiceQueryCtrl,
                  decoration: const InputDecoration(hintText: "Type medical question...", border: OutlineInputBorder()),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.send, color: Color(0xFF0D9488)),
                onPressed: () {
                  if (_voiceQueryCtrl.text.isNotEmpty) {
                    _askVoice(_voiceQueryCtrl.text);
                    _voiceQueryCtrl.clear();
                  }
                },
              )
            ],
          ),
          const SizedBox(height: 20),
          if (_isVoiceLoading) const CircularProgressIndicator(color: Color(0xFF0D9488)),
          if (_voiceResponse != null)
            Card(
              color: const Color(0xFFF0FDFA),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.volume_up, color: Color(0xFF0D9488)),
                        SizedBox(width: 8),
                        Text("MediSync Voice Response", style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0F766E))),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_voiceResponse!, style: const TextStyle(fontSize: 14, height: 1.4)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

