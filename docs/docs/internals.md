# Jane Internals

## Document Data Model

`Jane` stores data from plugins in a document database. The hierarchical data model is as follows:

* `DocumentType`: The document category. Determined from the installed plugins.
* `Document`: One document of a certain type. Can have multiple indices.
* `DocumentIndex`: The indices of a certain document.
* `DocumentIndexAttachments`: The attachments for one index.

