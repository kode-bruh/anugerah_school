from odoo import api, fields, models, exceptions

class ClassStage(models.Model):
	_name = "asm.class.stage"
	_inherit = "asm.class.stage"

	payment_template_ids = fields.One2many("as.payment.template", "stage_id", string="Template Tagihan", required=True)


class StudentTransfer(models.Model):
	_name = "as.student_transfer"
	_inherit = "as.student_transfer"

	def action_validate(self):
		super(StudentTransfer, self).action_validate()

		# Switch and reset payment template for each student
		for i in self.item_ids:
			class_id = False
			if len(i.student_id.student_class_ids) > 0:
				class_id = sorted(i.student_id.student_class_ids, key=lambda i: i['class_id']['priority'])[-1].class_id
			if not class_id:
				raise exceptions.UserError("Tidak ditemukan kelas dengan nama '%s' untuk siswa '%s'" % (i.student_id.current_class, i.student_id.full_name))

			if not class_id.class_stage_id:
				raise exceptions.UserError("Jenjang pada kelas '%s' tidak diisi. Harap diisi dahulu sebelum membuat perpindahan kelas." % class_id.name)

			if len(class_id.class_stage_id.payment_template_ids) == 0:
				raise exceptions.UserError("Jenjang '%s' tidak memiliki Template Tagihan. Harap diisi dahulu sebelum membuat perpindahan kelas." % class_id.class_stage_id.name)

			# If all checks succeeded, proceed with changing template and resetting invoice rules
			# i.student_id.payment_template = class_id.class_stage_id.payment_template_id.id
			# i.student_id.populate_invoice_rules()