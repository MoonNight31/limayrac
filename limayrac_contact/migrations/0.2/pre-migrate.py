def migrate(cr, version):
    # L'ancienne étape unique « Signé » est éclatée en signature entreprise,
    # signature CFA puis validation. Un contrat déjà signé avait franchi tout
    # le circuit : il devient « Validé ».
    cr.execute("UPDATE limayrac_contract SET state = 'validated' WHERE state = 'signed'")
