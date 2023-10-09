const cds = require('@sap/cds');

cds.once('served', () => {
    const client = process.env?.sap_client || null;
    const dbkind = cds.db?.kind || null;
    if (client && dbkind == 'hana' && cds.db?.options?.credentials) {
        cds.db.options.credentials['databaseName'] = 'H00';
        cds.db.options.credentials['SESSIONVARIABLE:CLIENT'] = client;
        console.log(`Set client ${client} for database session successfully.`);
    } else {
        console.log(`Project is not configured to set client [client: ${client}, db: ${dbkind}].`);
    }
});
