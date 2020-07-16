db.createUser(
	{
		user : "footballdba",
		pwd : "lineker1990",
		roles : [
			{
				role: "readWrite",
				db: "footballDB"
			}
		]
	}
)
