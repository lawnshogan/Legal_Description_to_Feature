# **Legal Description (Excel) to GIS Feature Class (ArcGIS Pro)**

Automation scripts transform tabular legal descriptions into dynamic GIS feature classes within ArcGIS Pro. Effortless plotting and enhanced geospatial analysis.

# **Program Structure and Files:**

# 1. Definitions
- 'Pro': ArcGIS Pro. Version 2.9 or greater required
- 'Excel file': Lease data extract from NetSuite
- 'GIS Layer': Feature class updated from the extract information. Catalogs existing lease features
- 'PLSS': The BLM PLSS Intersected Survey feature class

# 2. Scripts and Required Files
-  ## **2.1**

LegalDescriptionToolbox.pyt

The Esri toolbox shell script for use in Pro. Basic required functionality, with the main execution a call to the legal_description_to_feature script.

-  ## **2.2**

legal_description_to_feature_v2.py

This is the main module for the application. Code imports the Excel file data, does the comparision to the GIS Layer, retrieves the PLSS features (if needed), and updates the GIS Layer.

-  ## **2.3**

config.py

Configuration values used across the modules. See the comments in the file on what is required to configure the scripts for the local environment. Note that some values are only used if the scripts are run standalone versus running from the Pro Toolbox.

-  ## **2.4**

ld_parser.py

Functions related to the Legal Description parsing for the PLSS data.

-  ## **2.5**

ld_patterns.py

This file contains the Python dictionary for mapping known PLSS 2nd Division to elements from the Legal Description. Keys/value pairs should be adjusted here (add/drop/change) to fine tune the pattern matching.

-  ## **2.6**

BLM_CO_PLSS_Intersected_Survey_Grid.gdb

A GDB is provided that contains the Colorado PLSS information used by the scripts.

Source data can be found at https://gbp-blm-egis.hub.arcgis.com/search?categories=cadastral&groupIds=97bb25da078444d4a04669405f77643b or https://gis.blm.gov/coarcgis/rest/services/cadastral/BLM_CO_PLSS/MapServer/4.

-  ## **2.7**

Working GDB

A dedicated GDB for the lease processing is recommended, but not required. The scripts use a file GDB for processing of intermediate steps. Layers are created/deleted. 
-  There are no special requirements for this GDB.
-  The recommendation for a dedicated GDB is to mitigate the potential clashes with other processing or data in the GDB.

# 3. Setup

-  ## **3.1**
Create a Pro project file or use an existing one

-  ## **3.2**
Place the PLSS GDB in a location accessible by the machine running the scripts

-  ## **3.3**
Place all Python scripts, including the toolbox file, in the same folder. 
- While not required, it is recommended that the scripts be in the same folder as the Pro project file.

- ## **3.4**
Check the instructions in the config.py file for values that are required by both the toolbox and the standalone scripts.

Additional values are required for the standalone scripts (i.e. values that the toolbox would have provided)

-  ## **3.5**
Add the toolbox to the Pro project

-  ## **3.6**
Add the PLSS GDB to the Pro project

# 4. Execution

-  ## **4.1**
  
  The scripts are structure to run one of two ways:

1. From the Pro toolbox, with entry of parameters via the tool
2. As standalone scripts run from the Python command line or a Python IDE (e.g. Visual Studio Code, IDLE, PyCharm, etc.)
      - legal_description_to_feature_v2.py

-  ## **4.2**
The scripts have not been tested in the Pro Python window. Recommendation is to avoid execution in that environment given known limitations and issues.
  
-  ## **4.3**
To run standalone, execute the legal_description_to_feature_v2.py script. The other modules will be imported as needed by this script.

# 5. Program Processing Steps

-  ## **5.1**
Input files and folders are verified to exist

-  ## **5.2**
Excel file is converted to pandas DataFrame and an initial data check is done against the values.

-  ## **5.3**
The remaining records are parsed into two groups: 1) existing transactions and 2) new transactions

-  ## **5.4**
Existing transactions are applied to the GIS layer. The update fields for these records in the GIS layer are overwritten by the data in the Excel file.

  -  ## **5.4.1**

Excel may have multiple rows for the transaction. If the attributes are not consistent across these rows for a given transaction, the transaction as a whole is rejected and the records posted to the audit logging.

  -  ## **5.5**
New transactions go through additional data checks

  -  ## **5.5.1**
A PLSS first division code is created from the meridian, township, range, and section information in the Excel. If any errors are found, the record is removed from further processing.

  -  ## **5.5.2**
A list of PLSS second division codes is created as needed. If the legal description is "All" (or some variation of that defined in the parser) or is blank, the second division code is set to ALL.

  -  ## **5.5.3**
Errors during the first/second division processing are posted to the audit logging. Records that cannot be reconcile enought for a PLSS search are dropped from further processing.

  -  ## **5.6**
The PLSS is queried for polygons based on the first/second division findings

  -  ## **5.6.1**
For 'ALL' second division, just the first division is used in the search, pulling in the full section.

  -  ## **5.6.2**
If no PLSS records are found for a transaction, an audit record is recorded.

  -  ## **5.7**
The PLSS polygon findings are dissolved down to one record for each new transaction. Data from the Excel file is added to the feature for the other attributes.

  -  ## **5.7.1**
KNOWN ISSUE! If there are multiple records in the Excel for the new transaction, only the attributes from the first one found is used. In the test data, not all these attributes align! For example, there often are different township, range, section numbers across the records. Which to use for the consolidated GIS layer??


## 6. Program Outputs
  -  ## **6.1**
Updated GIS layer

  -  ## **6.1.1** 
Existing transaction records have a subset of their values updated. See UPDATE_FIELDS in the config.py for the fields that are updated.

  -  ## **6.1.2**
For any new transaction records found in the Excel, the script attempts to find PLSS polygons, consolidate these, and add the records to the GIS layer.
1. The matching used is imperfect. New records must be verified!
2. The script will add up the total acres represented in the Excel file for the transaction (the transaction may comprise multiple rows in the file). It then totals the acre field in the records that had a PLSS match. If the the two totals do not match, an audit/error is posted. Likely a polygon is missing or there was a mismatch in the PLSS search.

  -  ## **6.1.3**
A log file is generated per the Config.py values. All messages and errors post to this file.

  -  ## **6.1.4**
An audit log file is posted to the same folder as the log file. This contains copies of the records with errors or audit issues, along with an error/audit message.

  -  ## **6.1.5**
An audit CSV file is also exported to the folder specified in the Config.py file. This file mirrors the audit log file, just in a CSV format that can be imported into Excel.
