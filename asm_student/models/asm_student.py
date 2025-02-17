from odoo import fields, models, api, exceptions

class Student(models.Model):
	_name = "asm.student"
	_inherit = ['mail.thread']
	_description = "Student"
	_rec_name = "full_name"

	active = fields.Boolean(default=True, tracking=True)
	nias = fields.Char(string="Nomor Induk Anugerah School", tracking=True)
	full_name = fields.Char(string="Nama Lengkap", required=True, tracking=True)
	nipd = fields.Char(string="NIS/Nomor Induk PD", tracking=True)
	gender = fields.Selection([('L', 'Laki-laki'), ('P', 'Perempuan')], default="L", string="Jenis Kelamin", required=True)
	nisn = fields.Char(string="NISN", tracking=True)
	birth_place = fields.Char(string="Tempat Lahir", required=True)
	birth_date = fields.Date(string="Tanggal Lahir", required=True)
	nik = fields.Char(string="NIK/No. KITAS")
	religion = fields.Many2one("as.selection", ondelete="restrict", string="Agama", required=True, domain="[('is_religion', '=', True)]")
	address = fields.Char(string="Alamat Lengkap", required=True)
	rt = fields.Char(string="RT")
	rw = fields.Char(string="RW")
	village = fields.Char(string="Nama Dusun", default="-")
	sub_district = fields.Char(string="Nama Kelurahan/Desa", default="-")
	district = fields.Char(string="Kecamatan", default="-")
	zip_code = fields.Char(string="Kode Pos")
	address_type = fields.Many2one("as.selection", ondelete="restrict", string="Jenis Tempat Tinggal", required=True, domain="[('is_address_type', '=', True)]")
	transportation = fields.Many2one("as.selection", ondelete="set null", string="Transportasi", domain="[('is_transportation_type', '=', True)]")
	home_phone_number = fields.Char(string="Nomor Telepon Rumah")
	cellphone_number = fields.Char(string="Nomor HP")
	email = fields.Char(string="Email")
	skhun_number = fields.Char(string="Nomor SKHUN SMP/MTs")
	receive_kps = fields.Selection([('1', 'Ya'), ('0', 'Tidak')], string="Penerima KPS", default="1")
	kps_number = fields.Char(string="Nomor KPS")

	father_name = fields.Char(string="Nama Ayah Kandung")
	father_nik = fields.Char(string="NIK Ayah")
	father_birth_year = fields.Integer(string="Tahun Lahir Ayah")
	father_education = fields.Many2one("as.selection", ondelete="set null", string="Pendidikan Ayah", domain="[('is_education_level', '=', True)]")
	father_work = fields.Many2one("as.selection", ondelete="set null", string="Pekerjaan Ayah", domain="[('is_work_field', '=', True)]")	
	father_income = fields.Many2one("as.selection", ondelete="set null", string="Penghasilan Ayah", domain="[('is_income_rate', '=', True)]")	

	mother_name = fields.Char(string="Nama Ibu Kandung")
	mother_nik = fields.Char(string="NIK Ibu")
	mother_birth_year = fields.Integer(string="Tahun Lahir Ibu")
	mother_education = fields.Many2one("as.selection", ondelete="set null", string="Pendidikan Ibu", domain="[('is_education_level', '=', True)]")
	mother_work = fields.Many2one("as.selection", ondelete="set null", string="Pekerjaan Ibu", domain="[('is_work_field', '=', True)]")	
	mother_income = fields.Many2one("as.selection", ondelete="set null", string="Penghasilan Ibu", domain="[('is_income_rate', '=', True)]")	

	guardian_name = fields.Char(string="Nama Wali")
	guardian_nik = fields.Char(string="NIK Wali")
	guardian_birth_year = fields.Integer(string="Tahun Lahir Wali")
	guardian_education = fields.Many2one("as.selection", ondelete="set null", string="Pendidikan Wali", domain="[('is_education_level', '=', True)]")
	guardian_work = fields.Many2one("as.selection", ondelete="set null", string="Pekerjaan Wali", domain="[('is_work_field', '=', True)]")	
	guardian_income = fields.Many2one("as.selection", ondelete="set null", string="Penghasilan Wali", domain="[('is_income_rate', '=', True)]")	

	national_exam_number = fields.Char(string="Nomor Peserta UN SMP/MTs")
	diploma_number = fields.Char(string="Nomor Seri Ijazah SMP/MTs")
	receive_kip = fields.Selection([('1', 'Ya'), ('0', 'Tidak')], string="Menerima KIP", default="0")
	kip_number = fields.Char(string="Nomor KIP")
	kip_behalf_name = fields.Char(string="Nama di KIP")
	kks_number = fields.Char(string="Nomor KKS")
	birth_cert_number = fields.Char(string="No. Registrasi Akta Lahir")
	bank = fields.Char(string="Bank", tracking=True)
	bank_account_number = fields.Char(string="Nomor Rekening Bank", tracking=True)
	bank_behalf_name = fields.Char(string="Rekening Atas Nama", tracking=True)
	needs_pip = fields.Selection([('1', 'Ya'), ('0', 'Tidak')], string="Layak PIP", default="0")	
	reason_need_pip = fields.Char(string="Alasan Layak PIP")
	special_needs = fields.Many2one("as.selection", ondelete="set null", string="Kebutuhan Khusus", domain="[('is_special_needs', '=', True)]")
	previous_school = fields.Char(string="Sekolah Asal")
	child_number = fields.Integer(string="Anak Ke-", default=1)
	latitude = fields.Float(string="Lintang", default=0)
	longitude = fields.Float(string="Bujur", default=0)
	kk = fields.Char(string="No. KK", tracking=True)
	weight = fields.Char(string="Berat Badan")
	height = fields.Char(string="Tinggi Badan")
	head_circumference = fields.Char(string="Lingkar Kepala")
	sibling_count = fields.Integer(string="Jumlah Saudara Kandung", default=0)
	server_url = fields.Char(string="URL Dokumen", tracking=True)

	# Fields from different models inserted below

	student_class_ids = fields.One2many("as.class_student", 'student_id', string="Jejak Kelas Siswa")
	current_class = fields.Char(string="Kelas Siswa", compute="_get_current_class", store=True, tracking=True)
	state_id = fields.Many2one("asm.state", ondelete="restrict", string="Status", required=True, domain="[('student_state', '=', True)]")

	def write(self, values):
		if 'active' in values:
			supervisor_group = self.env.ref('asm_student.supervisor_group')
			if self.env.user.id not in supervisor_group.users.ids:
				raise exceptions.UserError("Anda tidak dapat melakukan Archive/Unarchive. Anda bukan Supervisor module Student Management.")
		return super(Student, self).write(values)

	@api.depends('student_class_ids', 'student_class_ids.term_id', 'student_class_ids.class_id')
	def _get_current_class(self):
		for i in self:
			if len(i.student_class_ids) > 0:
				last_class = sorted(i.student_class_ids, key=lambda i: i['class_id']['priority'])[-1]
				i.current_class = "%s (%s)" % (last_class.class_id.name, last_class.term_id.name)
			else:
				i.current_class = "Unassigned"

	@api.model
	def default_get(self, fields):
		res = super(Student, self).default_get(fields)
		res['state_id'] = self.env['asm.state'].search([('default', '=', True), ('student_state', '=', True)], limit=1).id
		return res

	def action_move_class(self):
		for i in self:
			return {
				'name': 'Pindah Kelas',
				'view_mode': 'form',
				'view_type': 'form',
				'res_model': 'as.move_class.wiz',
				'context': {'default_student_id': i.id},
				'target': 'new',
				'type': 'ir.actions.act_window',
			}

	def action_change_class(self):
		for i in self:
			return {
				'name': 'Ubah Kelas',
				'view_mode': 'form',
				'view_type': 'form',
				'res_model': 'as.class_student.wiz',
				'context': {'default_student_id': i.id},
				'target': 'new',
				'type': 'ir.actions.act_window',
			}

class SelectionData(models.Model):
	_name = "as.selection"
	_description = "Selection Data"

	name = fields.Char(string="Nama", required=True)
	value = fields.Char(string="Nilai")
	is_religion = fields.Boolean(string="Sebuah Agama?")
	is_address_type = fields.Boolean(string="Sebuah Jenis Tempat Tinggal?")
	is_transportation_type = fields.Boolean(string="Sebuah Jenis Kendaraan?")
	is_education_level = fields.Boolean(string="Sebuah Jenjang Pendidikan?")
	is_work_field = fields.Boolean(string="Sebuah Bidang Pekerjaan?")
	is_income_rate = fields.Boolean(string="Sebuah Tingkat Penghasilan?")
	is_special_needs = fields.Boolean(string="Sebuah Kebutuhan Khusus?")
	is_class_stage = fields.Boolean(string="Sebuah Jenjang Kelas?")
	is_class_alt = fields.Boolean(string="Sebuah Pilihan Kelas?")