const cds = require('@sap/cds');

cds.once('served', () => {
    const client = process.env?.sap_client || null,
        user = cds.db?.options?.credentials?.user || null,
        dbkind = cds.db?.kind || null;
    if (user && client && dbkind == 'hana') {
        cds.db.run(`CALL SET_CLIENT(client => '${client}')`)
            .then(() => console.log(`Set client ${client} for user ${user} successfully.`))
            .catch(error => console.error(`ERROR: Could not set client ${client} for user ${user}. ${error}`));
    } else {
        console.log(`Project is not configured to set client [user: ${user}, client: ${client}, db: ${dbkind}].`);
    }
});
