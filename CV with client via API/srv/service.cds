using {
    LOG,
    SAP
} from '../db/schema';

service CALCVIEWS {
    @cds.persistence.exists
    entity SAPDATA   as projection on SAP.DATA;
};

service LOGS {
    entity LOG_TABLE as projection on LOG.TABLE;
};
