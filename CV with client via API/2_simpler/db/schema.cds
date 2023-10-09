context SAP {
    @cds.persistence.exists
    @cds.persistence.calcview
    entity DATA {
        key MANDT : String(3);
        key ID    : Integer;
            VALUE : Integer;
    };
};

// context LOG {
//     @cds.persistence.exists
//     entity TABLE {
//         TIME     : DateTime;
//         EXECUTER : String(255);
//         SUBJECT  : String(255);
//         CLIENT   : String(3);
//         RESULT   : String(1000);
//     };
// };
