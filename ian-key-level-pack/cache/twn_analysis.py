#!/usr/bin/env python3
"""TWN Key Level Analysis — saves cache data + runs full scoring."""
import json, os, sys

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache")
DATA_DIR = os.path.join(CACHE_DIR, "data", "TWN")

# ============================================================
# Save raw data to cache (embedded from TradingView MCP)
# ============================================================

# W1 data (300 bars, Aug 2020 - June 2026)
W1_BARS = [
    {"time": 1598595300, "open": 1093.25, "high": 1110, "low": 1083, "close": 1098, "volume": 57403},
    {"time": 1599200100, "open": 1097.25, "high": 1107.75, "low": 1090.25, "close": 1100.5, "volume": 40266},
    {"time": 1599804900, "open": 1112.5, "high": 1131, "low": 1110.5, "close": 1119.5, "volume": 30108},
    {"time": 1600409700, "open": 1103.25, "high": 1106.5, "low": 1057.5, "close": 1067.75, "volume": 45132},
    {"time": 1601014500, "open": 1086, "high": 1109, "low": 1081.25, "close": 1093.75, "volume": 8420},
    {"time": 1601619300, "open": 1089.5, "high": 1125.75, "low": 1089.25, "close": 1121.75, "volume": 24783},
    {"time": 1602224100, "open": 1123.25, "high": 1130.25, "low": 1107.75, "close": 1112, "volume": 49563},
    {"time": 1602828900, "open": 1117, "high": 1128, "low": 1113.25, "close": 1123.5, "volume": 55977},
    {"time": 1603433700, "open": 1122, "high": 1125.5, "low": 1077, "close": 1087.5, "volume": 54338},
    {"time": 1604038500, "open": 1090, "high": 1132.25, "low": 1088.25, "close": 1128.75, "volume": 66286},
    {"time": 1604643300, "open": 1141, "high": 1163.5, "low": 1137.75, "close": 1162.5, "volume": 56962},
    {"time": 1605248100, "open": 1179.5, "high": 1209.5, "low": 1178.25, "close": 1202, "volume": 37262},
    {"time": 1605852900, "open": 1210.75, "high": 1212.75, "low": 1192.75, "close": 1207.25, "volume": 68193},
    {"time": 1606457700, "open": 1189, "high": 1234, "low": 1179.75, "close": 1231, "volume": 43176},
    {"time": 1607062500, "open": 1233.75, "high": 1252.75, "low": 1231.5, "close": 1234.75, "volume": 31133},
    {"time": 1607667300, "open": 1236, "high": 1249.75, "low": 1227, "close": 1242.5, "volume": 41966},
    {"time": 1608272100, "open": 1255, "high": 1257.25, "low": 1232, "close": 1254.5, "volume": 51753},
    {"time": 1608876900, "open": 1264.75, "high": 1281, "low": 1262.75, "close": 1277, "volume": 31729},
    {"time": 1609481700, "open": 1295.75, "high": 1351.25, "low": 1294.75, "close": 1347.25, "volume": 110567},
    {"time": 1610086500, "open": 1349.25, "high": 1403, "low": 1340, "close": 1368.25, "volume": 382426},
    {"time": 1610691300, "open": 1367.5, "high": 1409.5, "low": 1340.25, "close": 1399.75, "volume": 447611},
    {"time": 1611296100, "open": 1399, "high": 1402.75, "low": 1322.25, "close": 1322.75, "volume": 452421},
    {"time": 1611900900, "open": 1322.75, "high": 1395, "low": 1320, "close": 1382.5, "volume": 260785},
    {"time": 1612505700, "open": 1381.75, "high": 1424.5, "low": 1377.5, "close": 1424.5, "volume": 62833},
    {"time": 1613110500, "open": 1423.25, "high": 1444, "low": 1409.75, "close": 1424.75, "volume": 329409},
    {"time": 1613715300, "open": 1425, "high": 1447.75, "low": 1307, "close": 1386, "volume": 382400},
    {"time": 1614320100, "open": 1386.25, "high": 1420.5, "low": 1359.75, "close": 1384.5, "volume": 385115},
    {"time": 1614924900, "open": 1383.25, "high": 1423.25, "low": 1363.5, "close": 1420.25, "volume": 310921},
    {"time": 1615529700, "open": 1417.5, "high": 1443.75, "low": 1401.25, "close": 1405.75, "volume": 253241},
    {"time": 1616134500, "open": 1402.75, "high": 1442, "low": 1398.5, "close": 1441.25, "volume": 373630},
    {"time": 1616739300, "open": 1440.25, "high": 1471.25, "low": 1437.75, "close": 1469.5, "volume": 141114},
    {"time": 1617344100, "open": 1470, "high": 1488.25, "low": 1462.75, "close": 1476.75, "volume": 223112},
    {"time": 1617948900, "open": 1477, "high": 1509.75, "low": 1458.5, "close": 1509.75, "volume": 278156},
    {"time": 1618553700, "open": 1509.25, "high": 1536.5, "low": 1505.5, "close": 1524.75, "volume": 412514},
    {"time": 1619158500, "open": 1524.75, "high": 1571.5, "low": 1523.75, "close": 1547.25, "volume": 230841},
    {"time": 1619763300, "open": 1546.5, "high": 1555.75, "low": 1472.25, "close": 1528.75, "volume": 328033},
    {"time": 1620368100, "open": 1528.25, "high": 1539.25, "low": 1326.75, "close": 1394.75, "volume": 509005},
    {"time": 1620972900, "open": 1393, "high": 1461.5, "low": 1339.5, "close": 1442, "volume": 315454},
    {"time": 1621577700, "open": 1440.25, "high": 1486.5, "low": 1422.5, "close": 1485.25, "volume": 334848},
    {"time": 1622182500, "open": 1484.75, "high": 1517.5, "low": 1479, "close": 1500.5, "volume": 221988},
    {"time": 1622787300, "open": 1500.75, "high": 1518.75, "low": 1470.25, "close": 1510, "volume": 167166},
    {"time": 1623392100, "open": 1510, "high": 1523.25, "low": 1495.5, "close": 1511.75, "volume": 227538},
    {"time": 1623996900, "open": 1512.25, "high": 1534.75, "low": 1480, "close": 1524, "volume": 394658},
    {"time": 1624601700, "open": 1523.5, "high": 1533.5, "low": 1506.75, "close": 1520.75, "volume": 189466},
    {"time": 1625206500, "open": 1520.75, "high": 1548.25, "low": 1504.5, "close": 1516, "volume": 219457},
    {"time": 1625811300, "open": 1517.25, "high": 1555.5, "low": 1517.25, "close": 1553.5, "volume": 217199},
    {"time": 1626416100, "open": 1552.25, "high": 1555, "low": 1503.5, "close": 1524, "volume": 281030},
    {"time": 1627020900, "open": 1525, "high": 1530, "low": 1469, "close": 1494.25, "volume": 327761},
    {"time": 1627625700, "open": 1496.75, "high": 1535, "low": 1494.25, "close": 1523, "volume": 184455},
    {"time": 1628230500, "open": 1523.25, "high": 1525.75, "low": 1476.75, "close": 1477.25, "volume": 208468},
    {"time": 1628835300, "open": 1477.25, "high": 1480.25, "low": 1414.75, "close": 1423.75, "volume": 329748},
    {"time": 1629440100, "open": 1427.5, "high": 1507.25, "low": 1423.25, "close": 1503.25, "volume": 367198},
    {"time": 1630044900, "open": 1497.5, "high": 1534.75, "low": 1497.5, "close": 1532, "volume": 219833},
    {"time": 1630649700, "open": 1530.5, "high": 1540, "low": 1495.75, "close": 1529.75, "volume": 213054},
    {"time": 1631254500, "open": 1528.75, "high": 1538, "low": 1510.75, "close": 1518.25, "volume": 186845},
    {"time": 1631859300, "open": 1519.5, "high": 1521.25, "low": 1459.75, "close": 1516, "volume": 344226},
    {"time": 1632464100, "open": 1517, "high": 1523.75, "low": 1439.5, "close": 1448, "volume": 284743},
    {"time": 1633068900, "open": 1448.5, "high": 1471, "low": 1411, "close": 1455.5, "volume": 270567},
    {"time": 1633673700, "open": 1455.5, "high": 1465.75, "low": 1422.75, "close": 1461.5, "volume": 238952},
    {"time": 1634278500, "open": 1461, "high": 1485, "low": 1453, "close": 1469.5, "volume": 236555},
    {"time": 1634883300, "open": 1469.5, "high": 1491.25, "low": 1458.5, "close": 1476, "volume": 278435},
    {"time": 1635488100, "open": 1473.75, "high": 1507, "low": 1470.25, "close": 1506, "volume": 222280},
    {"time": 1636092900, "open": 1505.5, "high": 1539.75, "low": 1503, "close": 1532, "volume": 250481},
    {"time": 1636697700, "open": 1532, "high": 1576.25, "low": 1530, "close": 1564.5, "volume": 209244},
    {"time": 1637302500, "open": 1564.75, "high": 1568.5, "low": 1516.25, "close": 1517.5, "volume": 326039},
    {"time": 1637907300, "open": 1515, "high": 1557.25, "low": 1491.25, "close": 1551.5, "volume": 335261},
    {"time": 1638512100, "open": 1552.5, "high": 1580.5, "low": 1536.75, "close": 1564.75, "volume": 214640},
    {"time": 1639116900, "open": 1565.25, "high": 1576.25, "low": 1535.25, "close": 1564.5, "volume": 219218},
    {"time": 1639721700, "open": 1565, "high": 1587.5, "low": 1537.25, "close": 1581.25, "volume": 252521},
    {"time": 1640326500, "open": 1581.25, "high": 1611.5, "low": 1579.25, "close": 1603.5, "volume": 167520},
    {"time": 1640931300, "open": 1606.25, "high": 1629.5, "low": 1591.25, "close": 1593, "volume": 266501},
    {"time": 1641536100, "open": 1593.75, "high": 1637.75, "low": 1582.5, "close": 1606.75, "volume": 304641},
    {"time": 1642140900, "open": 1608, "high": 1626.5, "low": 1563.5, "close": 1568.75, "volume": 458629},
    {"time": 1642745700, "open": 1569.5, "high": 1577, "low": 1485.75, "close": 1491.75, "volume": 211222},
    {"time": 1643350500, "open": 1490, "high": 1581.25, "low": 1478.75, "close": 1568.75, "volume": 134114},
    {"time": 1643955300, "open": 1568.5, "high": 1614, "low": 1541.25, "close": 1600.75, "volume": 286214},
    {"time": 1644560100, "open": 1602.25, "high": 1611.25, "low": 1559, "close": 1597.75, "volume": 296476},
    {"time": 1645164900, "open": 1596.25, "high": 1601.5, "low": 1507.75, "close": 1540.75, "volume": 332434},
    {"time": 1645769700, "open": 1540.75, "high": 1579.25, "low": 1523.75, "close": 1544, "volume": 321716},
    {"time": 1646374500, "open": 1547, "high": 1552, "low": 1451.25, "close": 1509.25, "volume": 354963},
    {"time": 1646979300, "open": 1514.75, "high": 1539.25, "low": 1467.5, "close": 1529.25, "volume": 345032},
    {"time": 1647584100, "open": 1531, "high": 1559.25, "low": 1522.25, "close": 1545, "volume": 329682},
    {"time": 1648188900, "open": 1545, "high": 1558, "low": 1518.25, "close": 1538, "volume": 212653},
    {"time": 1648793700, "open": 1538, "high": 1573, "low": 1502.5, "close": 1517, "volume": 241031},
    {"time": 1649398500, "open": 1518.25, "high": 1523, "low": 1480.75, "close": 1482.5, "volume": 275097},
    {"time": 1650003300, "open": 1482, "high": 1502.75, "low": 1465, "close": 1483.25, "volume": 343068},
    {"time": 1650608100, "open": 1483.5, "high": 1485.5, "low": 1417.75, "close": 1457.25, "volume": 346411},
    {"time": 1651212900, "open": 1459.75, "high": 1476.5, "low": 1416.25, "close": 1434.5, "volume": 293815},
    {"time": 1651817700, "open": 1436.25, "high": 1440.25, "low": 1362.5, "close": 1388.5, "volume": 342919},
    {"time": 1652422500, "open": 1386, "high": 1423.25, "low": 1381.5, "close": 1412.75, "volume": 275922},
    {"time": 1653027300, "open": 1413.5, "high": 1428, "low": 1386, "close": 1427.25, "volume": 389065},
    {"time": 1653632100, "open": 1409.75, "high": 1455.75, "low": 1409, "close": 1448, "volume": 257419},
    {"time": 1654236900, "open": 1447.5, "high": 1448.75, "low": 1415.25, "close": 1427.25, "volume": 275626},
    {"time": 1654841700, "open": 1428.75, "high": 1430, "low": 1343.75, "close": 1349.25, "volume": 374405},
    {"time": 1655446500, "open": 1347.5, "high": 1376.5, "low": 1317.5, "close": 1337.75, "volume": 363561},
    {"time": 1656051300, "open": 1337, "high": 1367.25, "low": 1229.75, "close": 1234.75, "volume": 313636},
    {"time": 1656656100, "open": 1235, "high": 1255.75, "low": 1199.75, "close": 1247, "volume": 304008},
    {"time": 1657260900, "open": 1245, "high": 1257.25, "low": 1201.75, "close": 1251.5, "volume": 280402},
    {"time": 1657865700, "open": 1251.5, "high": 1301.5, "low": 1245.75, "close": 1293, "volume": 234743},
    {"time": 1658470500, "open": 1293.5, "high": 1305.75, "low": 1277, "close": 1297.5, "volume": 247241},
    {"time": 1659075300, "open": 1296.75, "high": 1309.5, "low": 1263, "close": 1309.25, "volume": 246934},
    {"time": 1659680100, "open": 1309.25, "high": 1341.25, "low": 1294.25, "close": 1334.25, "volume": 193648},
    {"time": 1660284900, "open": 1335.25, "high": 1351.25, "low": 1334, "close": 1345, "volume": 163711},
    {"time": 1660889700, "open": 1345.5, "high": 1345.5, "low": 1310.25, "close": 1332.5, "volume": 294041},
    {"time": 1661494500, "open": 1331.5, "high": 1337.5, "low": 1266.5, "close": 1268.5, "volume": 233437},
    {"time": 1662099300, "open": 1267.5, "high": 1293, "low": 1250, "close": 1292, "volume": 196085},
    {"time": 1662704100, "open": 1290.75, "high": 1305, "low": 1254, "close": 1264.5, "volume": 218309},
    {"time": 1663308900, "open": 1264.5, "high": 1271.75, "low": 1226.75, "close": 1231, "volume": 308124},
    {"time": 1663913700, "open": 1231.5, "high": 1232.75, "low": 1160.25, "close": 1167.5, "volume": 344743},
    {"time": 1664518500, "open": 1168.25, "high": 1221.25, "low": 1153, "close": 1196.25, "volume": 246683},
    {"time": 1665123300, "open": 1196.25, "high": 1197.75, "low": 1113.75, "close": 1154, "volume": 354288},
    {"time": 1665728100, "open": 1153, "high": 1158.5, "low": 1112.25, "close": 1129.5, "volume": 335969},
    {"time": 1666332900, "open": 1132.25, "high": 1156.75, "low": 1114.75, "close": 1129.5, "volume": 355821},
    {"time": 1666937700, "open": 1130.25, "high": 1159, "low": 1126, "close": 1149.25, "volume": 262337},
    {"time": 1667542500, "open": 1150, "high": 1243.25, "low": 1146.5, "close": 1243.25, "volume": 300428},
    {"time": 1668147300, "open": 1241.5, "high": 1304.25, "low": 1241.5, "close": 1275.75, "volume": 325124},
    {"time": 1668752100, "open": 1274.25, "high": 1305.75, "low": 1264.75, "close": 1296.5, "volume": 340178},
    {"time": 1669356900, "open": 1296.25, "high": 1326.5, "low": 1267.25, "close": 1307, "volume": 247152},
    {"time": 1669961700, "open": 1306, "high": 1320.75, "low": 1265.5, "close": 1290.25, "volume": 240272},
    {"time": 1670566500, "open": 1289.5, "high": 1296.25, "low": 1261.25, "close": 1268.5, "volume": 269745},
    {"time": 1671171300, "open": 1269, "high": 1272.25, "low": 1237, "close": 1247.5, "volume": 268878},
    {"time": 1671776100, "open": 1247.25, "high": 1265.5, "low": 1222.25, "close": 1241.75, "volume": 194415},
    {"time": 1672380900, "open": 1240.75, "high": 1266.75, "low": 1223.25, "close": 1264, "volume": 194676},
    {"time": 1672985700, "open": 1264.25, "high": 1319.75, "low": 1259.5, "close": 1302.25, "volume": 296484},
    {"time": 1673590500, "open": 1302.75, "high": 1331.75, "low": 1300.5, "close": 1325.25, "volume": 170644},
    {"time": 1674195300, "open": 1325.75, "high": 1381.5, "low": 1322, "close": 1381, "volume": 114061},
    {"time": 1674800100, "open": 1383.5, "high": 1383.5, "low": 1333, "close": 1364.5, "volume": 279731},
    {"time": 1675404900, "open": 1363.5, "high": 1376.5, "low": 1339, "close": 1363.5, "volume": 227437},
    {"time": 1676009700, "open": 1364.75, "high": 1379.5, "low": 1345.75, "close": 1356.25, "volume": 311958},
    {"time": 1676614500, "open": 1355.75, "high": 1377.5, "low": 1345.5, "close": 1362, "volume": 239256},
    {"time": 1677219300, "open": 1361.25, "high": 1373.75, "low": 1342.5, "close": 1369.25, "volume": 208489},
    {"time": 1677824100, "open": 1368.75, "high": 1394.25, "low": 1352.5, "close": 1355.25, "volume": 274131},
    {"time": 1678428900, "open": 1355.5, "high": 1361.75, "low": 1319.5, "close": 1351.25, "volume": 334507},
    {"time": 1679033700, "open": 1350.75, "high": 1397.5, "low": 1334.25, "close": 1393, "volume": 340845},
    {"time": 1679638500, "open": 1393, "high": 1397.25, "low": 1369.25, "close": 1388, "volume": 236925},
    {"time": 1680243300, "open": 1387.75, "high": 1403.25, "low": 1371.5, "close": 1377.5, "volume": 132737},
    {"time": 1680848100, "open": 1376.5, "high": 1397.25, "low": 1370.75, "close": 1392.75, "volume": 207861},
    {"time": 1681452900, "open": 1392.75, "high": 1394.75, "low": 1358.5, "close": 1359.5, "volume": 279854},
    {"time": 1682057700, "open": 1359, "high": 1365.25, "low": 1330, "close": 1356.75, "volume": 245559},
    {"time": 1682662500, "open": 1357.5, "high": 1369, "low": 1351.5, "close": 1364.25, "volume": 187415},
    {"time": 1683267300, "open": 1365, "high": 1377.25, "low": 1346.5, "close": 1353.5, "volume": 200628},
    {"time": 1683872100, "open": 1350.75, "high": 1413.5, "low": 1345.5, "close": 1410.25, "volume": 276995},
    {"time": 1684476900, "open": 1410.25, "high": 1433, "low": 1390, "close": 1429.5, "volume": 453351},
    {"time": 1685081700, "open": 1430, "high": 1450.25, "low": 1411.75, "close": 1440.25, "volume": 255962},
    {"time": 1685686500, "open": 1440, "high": 1464.25, "low": 1437, "close": 1457.25, "volume": 235355},
    {"time": 1686291300, "open": 1456.75, "high": 1500.5, "low": 1454.25, "close": 1490.75, "volume": 259774},
    {"time": 1686896100, "open": 1491, "high": 1493.5, "low": 1464.25, "close": 1467.75, "volume": 252073},
    {"time": 1687500900, "open": 1467.5, "high": 1474.25, "low": 1434.75, "close": 1444.5, "volume": 298865},
    {"time": 1688105700, "open": 1443.75, "high": 1472.75, "low": 1418.25, "close": 1427, "volume": 232137},
    {"time": 1688710500, "open": 1427.5, "high": 1492, "low": 1418.5, "close": 1488.75, "volume": 239910},
    {"time": 1689315300, "open": 1488.75, "high": 1503.5, "low": 1454.75, "close": 1471.75, "volume": 274842},
    {"time": 1689920100, "open": 1473, "high": 1502, "low": 1464.75, "close": 1498, "volume": 397809},
    {"time": 1690524900, "open": 1498.5, "high": 1515.5, "low": 1427.5, "close": 1457.75, "volume": 280980},
    {"time": 1691129700, "open": 1457, "high": 1477.25, "low": 1437.5, "close": 1444.5, "volume": 237771},
    {"time": 1691734500, "open": 1444.25, "high": 1445.25, "low": 1402.5, "close": 1414, "volume": 241496},
    {"time": 1692339300, "open": 1414.5, "high": 1449, "low": 1407.5, "close": 1414.25, "volume": 343251},
    {"time": 1692944100, "open": 1412.5, "high": 1448.25, "low": 1409.75, "close": 1437.25, "volume": 214214},
    {"time": 1693548900, "open": 1437.25, "high": 1448, "low": 1417.75, "close": 1426.5, "volume": 186512},
    {"time": 1694153700, "open": 1427.75, "high": 1460.5, "low": 1409.5, "close": 1459.5, "volume": 247838},
    {"time": 1694758500, "open": 1459, "high": 1461, "low": 1387.75, "close": 1409.5, "volume": 374232},
    {"time": 1695363300, "open": 1409, "high": 1426.5, "low": 1399.25, "close": 1425, "volume": 220504},
    {"time": 1695968100, "open": 1426.25, "high": 1430.75, "low": 1393, "close": 1427.75, "volume": 262097},
    {"time": 1696572900, "open": 1426, "high": 1461.5, "low": 1419.25, "close": 1450, "volume": 239115},
    {"time": 1697177700, "open": 1450, "high": 1451.75, "low": 1399.5, "close": 1412.5, "volume": 312803},
    {"time": 1697782500, "open": 1412, "high": 1414.25, "low": 1376, "close": 1392.5, "volume": 373495},
    {"time": 1698387300, "open": 1392, "high": 1428.5, "low": 1375, "close": 1427.5, "volume": 278135},
    {"time": 1698992100, "open": 1428, "high": 1458.25, "low": 1423.25, "close": 1446.5, "volume": 233928},
    {"time": 1699596900, "open": 1446.75, "high": 1491.25, "low": 1446.5, "close": 1487.75, "volume": 274711},
    {"time": 1700201700, "open": 1487.5, "high": 1505.25, "low": 1479.25, "close": 1495.5, "volume": 362580},
    {"time": 1700806500, "open": 1495.25, "high": 1509.5, "low": 1481.5, "close": 1499.75, "volume": 275232},
    {"time": 1701411300, "open": 1500.25, "high": 1506.5, "low": 1481.5, "close": 1496, "volume": 210020},
    {"time": 1702016100, "open": 1496.5, "high": 1536.5, "low": 1492.5, "close": 1527, "volume": 239974},
    {"time": 1702620900, "open": 1528, "high": 1531.75, "low": 1499.5, "close": 1522.25, "volume": 333341},
    {"time": 1703225700, "open": 1521.5, "high": 1556.25, "low": 1520.25, "close": 1550.5, "volume": 191063},
    {"time": 1703830500, "open": 1551, "high": 1556.5, "low": 1510.25, "close": 1513.25, "volume": 192895},
    {"time": 1704435300, "open": 1513.75, "high": 1536.25, "low": 1501.75, "close": 1508.75, "volume": 230179},
    {"time": 1705040100, "open": 1508.5, "high": 1526.25, "low": 1470, "close": 1517.75, "volume": 343305},
    {"time": 1705644900, "open": 1519, "high": 1556.25, "low": 1514.75, "close": 1546, "volume": 429194},
    {"time": 1706249700, "open": 1545, "high": 1558.75, "low": 1534.5, "close": 1550, "volume": 231915},
    {"time": 1706854500, "open": 1550.5, "high": 1612.75, "low": 1539, "close": 1610.75, "volume": 113941},
    {"time": 1707459300, "open": 1611, "high": 1621.5, "low": 1575.5, "close": 1587.75, "volume": 220617},
    {"time": 1708064100, "open": 1587, "high": 1619.25, "low": 1583, "close": 1613.25, "volume": 395433},
    {"time": 1708668900, "open": 1612.25, "high": 1623.25, "low": 1596.75, "close": 1615.5, "volume": 204477},
    {"time": 1709273700, "open": 1615.75, "high": 1703, "low": 1612, "close": 1684.25, "volume": 359017},
    {"time": 1709878500, "open": 1684, "high": 1711, "low": 1673.5, "close": 1688.75, "volume": 335750},
    {"time": 1710483300, "open": 1688.5, "high": 1733.75, "low": 1684.25, "close": 1723.5, "volume": 417173},
    {"time": 1711088100, "open": 1723, "high": 1742.5, "low": 1697.75, "close": 1742.5, "volume": 334594},
    {"time": 1711692900, "open": 1742.5, "high": 1758, "low": 1704.75, "close": 1718.75, "volume": 231901},
    {"time": 1712297700, "open": 1717.75, "high": 1769, "low": 1710.75, "close": 1748.25, "volume": 328032},
    {"time": 1712902500, "open": 1747.75, "high": 1748, "low": 1616.25, "close": 1637, "volume": 487821},
    {"time": 1713507300, "open": 1638.25, "high": 1694.5, "low": 1629, "close": 1687.5, "volume": 470725},
    {"time": 1714112100, "open": 1689.75, "high": 1733.75, "low": 1685, "close": 1716.25, "volume": 292758},
    {"time": 1714716900, "open": 1716.25, "high": 1764.5, "low": 1712.75, "close": 1763.5, "volume": 261895},
    {"time": 1715321700, "open": 1763.75, "high": 1824.75, "low": 1762.75, "close": 1802.75, "volume": 276038},
    {"time": 1715926500, "open": 1802.25, "high": 1832.5, "low": 1784.75, "close": 1824.75, "volume": 305841},
    {"time": 1716531300, "open": 1824.5, "high": 1867, "low": 1792.5, "close": 1797.5, "volume": 377404},
    {"time": 1717136100, "open": 1797.25, "high": 1844.5, "low": 1779, "close": 1840.75, "volume": 251393},
    {"time": 1717740900, "open": 1840, "high": 1903.5, "low": 1819.75, "close": 1902.75, "volume": 262460},
    {"time": 1718345700, "open": 1902, "high": 1984.75, "low": 1890.5, "close": 1975, "volume": 367073},
    {"time": 1718950500, "open": 1975.25, "high": 1977, "low": 1899.75, "close": 1928.75, "volume": 330975},
    {"time": 1719555300, "open": 1929.5, "high": 1982.5, "low": 1909.25, "close": 1967.5, "volume": 234970},
    {"time": 1720160100, "open": 1965.75, "high": 2045.75, "low": 1959, "close": 1996.75, "volume": 312707},
    {"time": 1720764900, "open": 1998, "high": 2024.75, "low": 1911.25, "close": 1918, "volume": 376130},
    {"time": 1721369700, "open": 1919.5, "high": 1925, "low": 1818.5, "close": 1850, "volume": 388808},
    {"time": 1721974500, "open": 1852.25, "high": 1899, "low": 1797.25, "close": 1801.5, "volume": 372954},
    {"time": 1722579300, "open": 1800.5, "high": 1800.5, "low": 1581.5, "close": 1790, "volume": 444519},
    {"time": 1723184100, "open": 1787.5, "high": 1875.75, "low": 1777.75, "close": 1869, "volume": 210696},
    {"time": 1723788900, "open": 1868.5, "high": 1888.75, "low": 1829.5, "close": 1858.25, "volume": 248551},
    {"time": 1724393700, "open": 1858.25, "high": 1887.25, "low": 1836, "close": 1868.25, "volume": 273987},
    {"time": 1724998500, "open": 1868.5, "high": 1878.25, "low": 1749.5, "close": 1786, "volume": 327793},
    {"time": 1725603300, "open": 1787.25, "high": 1829.75, "low": 1726, "close": 1817.75, "volume": 296238},
    {"time": 1726208100, "open": 1815.75, "high": 1861.5, "low": 1796, "close": 1843.25, "volume": 196047},
    {"time": 1726812900, "open": 1844, "high": 1949.25, "low": 1833, "close": 1909, "volume": 376553},
    {"time": 1727417700, "open": 1907.75, "high": 1916.25, "low": 1828, "close": 1866, "volume": 232239},
    {"time": 1728022500, "open": 1866.25, "high": 1924.25, "low": 1861.25, "close": 1913, "volume": 213314},
    {"time": 1728627300, "open": 1912, "high": 1984.5, "low": 1903.5, "close": 1964.5, "volume": 260227},
    {"time": 1729232100, "open": 1964.5, "high": 1981.25, "low": 1923.75, "close": 1957.75, "volume": 298930},
    {"time": 1729836900, "open": 1958, "high": 1976.75, "low": 1858.25, "close": 1901.25, "volume": 305800},
    {"time": 1730441700, "open": 1902, "high": 1988.5, "low": 1895.5, "close": 1981.25, "volume": 250106},
    {"time": 1731046500, "open": 1980, "high": 1985, "low": 1887, "close": 1903, "volume": 279162},
    {"time": 1731651300, "open": 1900.25, "high": 1920.75, "low": 1868.5, "close": 1917, "volume": 254501},
    {"time": 1732256100, "open": 1918.5, "high": 1937.5, "low": 1832.5, "close": 1860.5, "volume": 358113},
    {"time": 1732860900, "open": 1860.5, "high": 1948, "low": 1848, "close": 1928.25, "volume": 186362},
    {"time": 1733465700, "open": 1928.5, "high": 1954, "low": 1903.75, "close": 1917, "volume": 173173},
    {"time": 1734070500, "open": 1917.5, "high": 1943.5, "low": 1873.75, "close": 1887.5, "volume": 234040},
    {"time": 1734675300, "open": 1886, "high": 1949.25, "low": 1878.25, "close": 1939.25, "volume": 267605},
    {"time": 1735280100, "open": 1942.25, "high": 1942.75, "low": 1883, "close": 1902.5, "volume": 166238},
    {"time": 1735884900, "open": 1903, "high": 1980.5, "low": 1897.75, "close": 1907.75, "volume": 264017},
    {"time": 1736489700, "open": 1906.25, "high": 1927.5, "low": 1843.25, "close": 1904.5, "volume": 412899},
    {"time": 1737094500, "open": 1904.25, "high": 1969, "low": 1903.25, "close": 1959, "volume": 197559},
    {"time": 1737699300, "open": 1959.25, "high": 1966.75, "low": 1820, "close": 1912, "volume": 127024},
    {"time": 1738304100, "open": 1913.5, "high": 1930.75, "low": 1853, "close": 1927.5, "volume": 221168},
    {"time": 1738908900, "open": 1927.5, "high": 1942.25, "low": 1904.5, "close": 1923.5, "volume": 191473},
    {"time": 1739513700, "open": 1923.75, "high": 1967.25, "low": 1915.5, "close": 1966, "volume": 216845},
    {"time": 1740118500, "open": 1965.75, "high": 1969.75, "low": 1859.5, "close": 1869.75, "volume": 329809},
    {"time": 1740723300, "open": 1863.25, "high": 1919, "low": 1846.5, "close": 1877, "volume": 295027},
    {"time": 1741328100, "open": 1874.5, "high": 1890, "low": 1806, "close": 1838, "volume": 259557},
    {"time": 1741932900, "open": 1836.75, "high": 1882, "low": 1834.25, "close": 1856, "volume": 189537},
    {"time": 1742537700, "open": 1856.75, "high": 1876.25, "low": 1798.5, "close": 1808.75, "volume": 322128},
    {"time": 1743142500, "open": 1809.5, "high": 1813.75, "low": 1687, "close": 1705.75, "volume": 235686},
    {"time": 1743746400, "open": 1707.75, "high": 1710, "low": 1423, "close": 1636.5, "volume": 667808},
    {"time": 1744351200, "open": 1638.25, "high": 1677.25, "low": 1603.75, "close": 1630.5, "volume": 294638},
    {"time": 1744956000, "open": 1630.5, "high": 1684, "low": 1586.75, "close": 1673.75, "volume": 293647},
    {"time": 1745560800, "open": 1673.75, "high": 1728.5, "low": 1664.5, "close": 1727.5, "volume": 210916},
    {"time": 1746165600, "open": 1725.25, "high": 1744.75, "low": 1683.25, "close": 1735.25, "volume": 287406},
    {"time": 1746770400, "open": 1736, "high": 1827.25, "low": 1727.5, "close": 1822, "volume": 209060},
    {"time": 1747375200, "open": 1822.5, "high": 1830, "low": 1790.75, "close": 1801.75, "volume": 232686},
    {"time": 1747980000, "open": 1801.25, "high": 1811.25, "low": 1737.5, "close": 1752, "volume": 340122},
    {"time": 1748584800, "open": 1749.5, "high": 1802.25, "low": 1720, "close": 1790.75, "volume": 219022},
    {"time": 1749189600, "open": 1790.5, "high": 1860.25, "low": 1786.5, "close": 1817, "volume": 221599},
    {"time": 1749794400, "open": 1818.25, "high": 1845.75, "low": 1804.5, "close": 1816.75, "volume": 211128},
    {"time": 1750399200, "open": 1817.25, "high": 1875.75, "low": 1782.75, "close": 1818.5, "volume": 385970},
    {"time": 1751004000, "open": 1816.75, "high": 1883.75, "low": 1811.75, "close": 1850, "volume": 217544},
    {"time": 1751608800, "open": 1849.75, "high": 1884.5, "low": 1828.5, "close": 1882.25, "volume": 188782},
    {"time": 1752213600, "open": 1881, "high": 1936, "low": 1858.25, "close": 1924.5, "volume": 207670},
    {"time": 1752818400, "open": 1924.75, "high": 1936.5, "low": 1893.75, "close": 1925, "volume": 268812},
    {"time": 1753423200, "open": 1925.75, "high": 1951.5, "low": 1901.25, "close": 1929.25, "volume": 329438},
    {"time": 1754028000, "open": 1929, "high": 1994.75, "low": 1900.75, "close": 1981, "volume": 207059},
    {"time": 1754632800, "open": 1980, "high": 2024.5, "low": 1974.75, "close": 2020, "volume": 179659},
    {"time": 1755237600, "open": 2020.25, "high": 2032.5, "low": 1952.5, "close": 1975.5, "volume": 223293},
    {"time": 1755842400, "open": 1975.25, "high": 2027.75, "low": 1970.5, "close": 2006, "volume": 354867},
    {"time": 1756447200, "open": 2005, "high": 2023.25, "low": 1956, "close": 2023, "volume": 195551},
    {"time": 1757052000, "open": 2023.5, "high": 2115.75, "low": 2010.25, "close": 2114, "volume": 229811},
    {"time": 1757656800, "open": 2113.25, "high": 2145, "low": 2096.75, "close": 2130.25, "volume": 225103},
    {"time": 1758261600, "open": 2130.75, "high": 2175.5, "low": 2098.25, "close": 2115.75, "volume": 415128},
    {"time": 1758866400, "open": 2115.75, "high": 2193.75, "low": 2107.5, "close": 2190.25, "volume": 212913},
    {"time": 1759471200, "open": 2191, "high": 2241.5, "low": 2180.5, "close": 2215.75, "volume": 191147},
    {"time": 1760076000, "open": 2215.75, "high": 2257.5, "low": 2089.25, "close": 2213.5, "volume": 340900},
    {"time": 1760680800, "open": 2215, "high": 2282.75, "low": 2192, "close": 2280.5, "volume": 227650},
    {"time": 1761285600, "open": 2280.25, "high": 2329.75, "low": 2275, "close": 2316.75, "volume": 409326},
    {"time": 1761890400, "open": 2317.75, "high": 2334.25, "low": 2231, "close": 2260, "volume": 294576},
    {"time": 1762495200, "open": 2260.5, "high": 2296.25, "low": 2215.75, "close": 2238, "volume": 261271},
    {"time": 1763100000, "open": 2237.5, "high": 2259.5, "low": 2149.5, "close": 2156.25, "volume": 393022},
    {"time": 1763704800, "open": 2156.25, "high": 2282.25, "low": 2136, "close": 2275.25, "volume": 414391},
    {"time": 1764309600, "open": 2275.5, "high": 2301.75, "low": 2256.25, "close": 2301.5, "volume": 187369},
    {"time": 1764914400, "open": 2301.75, "high": 2349.5, "low": 2298.5, "close": 2316, "volume": 196253},
    {"time": 1765519200, "open": 2315.75, "high": 2318.25, "low": 2242.75, "close": 2290.5, "volume": 264400},
    {"time": 1766124000, "open": 2289.75, "high": 2333.5, "low": 2232.5, "close": 2330, "volume": 244141},
    {"time": 1766728800, "open": 2330.5, "high": 2403.5, "low": 2327.25, "close": 2400, "volume": 144942},
    {"time": 1767333600, "open": 2401, "high": 2484.75, "low": 2399.5, "close": 2451.5, "volume": 261507},
    {"time": 1767938400, "open": 2452.75, "high": 2545, "low": 2447.5, "close": 2538.75, "volume": 270805},
    {"time": 1768543200, "open": 2539.25, "high": 2589.5, "low": 2509.5, "close": 2585.5, "volume": 291395},
    {"time": 1769148000, "open": 2585.5, "high": 2675.75, "low": 2577.75, "close": 2596.5, "volume": 439111},
    {"time": 1769752800, "open": 2594.75, "high": 2625.75, "low": 2509.75, "close": 2562, "volume": 366575},
    {"time": 1770357600, "open": 2562.25, "high": 2754, "low": 2557.25, "close": 2692.25, "volume": 234854},
    {"time": 1770962400, "open": 2693.75, "high": 2747.5, "low": 2660.5, "close": 2737, "volume": 116883},
    {"time": 1771567200, "open": 2735.5, "high": 2894.75, "low": 2714.25, "close": 2835.25, "volume": 446477},
    {"time": 1772172000, "open": 2834.5, "high": 2863, "low": 2605, "close": 2717.75, "volume": 439436},
    {"time": 1772776800, "open": 2719, "high": 2747.5, "low": 2506.25, "close": 2698, "volume": 376401},
    {"time": 1773381600, "open": 2703.25, "high": 2804.75, "low": 2647.75, "close": 2722.75, "volume": 290776},
    {"time": 1773986400, "open": 2721.5, "high": 2766.5, "low": 2599.5, "close": 2690.25, "volume": 487926},
    {"time": 1774591200, "open": 2693.25, "high": 2742.75, "low": 2568.25, "close": 2671.75, "volume": 300034},
    {"time": 1775196000, "open": 2671.75, "high": 2886.5, "low": 2656, "close": 2882.75, "volume": 227369},
    {"time": 1775800800, "open": 2880.75, "high": 3054.25, "low": 2859, "close": 3025, "volume": 247291},
    {"time": 1776405600, "open": 3026, "high": 3245.75, "low": 3019.75, "close": 3230.75, "volume": 370895},
    {"time": 1777010400, "open": 3229, "high": 3395.75, "low": 3221.25, "close": 3386.5, "volume": 333170},
    {"time": 1777615200, "open": 3382.75, "high": 3597.5, "low": 3360.5, "close": 3543, "volume": 281875},
    {"time": 1778220000, "open": 3542.5, "high": 3648.25, "low": 3444.75, "close": 3444.75, "volume": 270777},
    {"time": 1778824800, "open": 3455.25, "high": 3643.75, "low": 3357, "close": 3643, "volume": 279176},
    {"time": 1779429600, "open": 3637, "high": 3875, "low": 3624.25, "close": 3867.75, "volume": 216716},
]

print(f"W1 bars: {len(W1_BARS)}")

# Save W1 data
os.makedirs(DATA_DIR, exist_ok=True)
w1_meta = {
    "symbol": "TWN", "timeframe": "W1", "bar_count": len(W1_BARS),
    "last_price": W1_BARS[-1]["close"], "last_bar_time": W1_BARS[-1]["time"],
    "source": "tradingview-mcp"
}
with open(os.path.join(DATA_DIR, "W1.json"), "w") as f:
    json.dump({"data": W1_BARS, "meta": w1_meta}, f, indent=2)
print("Saved W1.json")

# Current price for reference
current_price = W1_BARS[-1]["close"]
print(f"Current price: {current_price}")

# ============================================================
# Quick swing point analysis
# ============================================================

def find_swing_highs(data, swing=1):
    swings = []
    for i in range(swing, len(data) - swing):
        if all(data[i]["high"] > data[i-j]["high"] and data[i]["high"] > data[i+j]["high"] for j in range(1, swing+1)):
            swings.append({"price": data[i]["high"], "idx": i, "time": data[i]["time"], "type": "high"})
    return swings

def find_swing_lows(data, swing=1):
    swings = []
    for i in range(swing, len(data) - swing):
        if all(data[i]["low"] < data[i-j]["low"] and data[i]["low"] < data[i+j]["low"] for j in range(1, swing+1)):
            swings.append({"price": data[i]["low"], "idx": i, "time": data[i]["time"], "type": "low"})
    return swings

# W1 swings (swing=1 for weekly)
w1_highs = find_swing_highs(W1_BARS, 1)
w1_lows = find_swing_lows(W1_BARS, 1)
print(f"W1 swing highs: {len(w1_highs)}, lows: {len(w1_lows)}")

# Cluster nearby swings
def cluster_levels(swings, cluster_range):
    if not swings:
        return []
    sorted_p = sorted(swings, key=lambda x: x["price"])
    clusters = []
    current = [sorted_p[0]]
    for p in sorted_p[1:]:
        if abs(p["price"] - sum(x["price"] for x in current) / len(current)) <= cluster_range:
            current.append(p)
        else:
            clusters.append(current)
            current = [p]
    clusters.append(current)
    
    results = []
    for c in clusters:
        prices = [x["price"] for x in c]
        results.append({
            "price": round(sum(prices) / len(prices), 1),
            "count": len(c), "type": c[0]["type"],
            "min": min(prices), "max": max(prices)
        })
    return results

w1_res = cluster_levels(w1_highs, 30)
w1_sup = cluster_levels(w1_lows, 30)

# Get top resistance and support near current price
w1_res_above = sorted([r for r in w1_res if r["price"] > current_price * 0.9], key=lambda x: x["price"])
w1_sup_below = sorted([s for s in w1_sup if s["price"] < current_price], key=lambda x: -x["price"])

print(f"\n=== W1 Resistance (near current price) ===")
for r in w1_res_above[:5]:
    print(f"  RES {r['price']} ({r['count']} swings)")

print(f"\n=== W1 Support (near current price) ===")
for s in w1_sup_below[:5]:
    print(f"  SUP {s['price']} ({s['count']} swings)")

# Collect candidate levels from W1 (nearest 3 each side)
candidates = []
for r in w1_res_above[:3]:
    candidates.append({"price": r["price"], "type": "RES", "tf": "W1"})
for s in w1_sup_below[:3]:
    candidates.append({"price": s["price"], "type": "SUP", "tf": "W1"})

# Add psychological round numbers near current price
for pn in [3000, 3200, 3400, 3500, 3600, 3800, 4000]:
    dist = abs(pn - current_price)
    if dist < 500:
        # Check if not already near an existing level
        nearby = any(abs(c["price"] - pn) < 30 for c in candidates)
        if not nearby:
            t = "RES" if pn > current_price else "SUP"
            candidates.append({"price": float(pn), "type": t, "tf": "psych"})

# Deduplicate candidates
seen = set()
unique = []
for c in candidates:
    key = round(c["price"], 0)
    if key not in seen:
        seen.add(key)
        unique.append(c)

print(f"\n=== Candidate levels ({len(unique)}) ===")
for c in sorted(unique, key=lambda x: abs(x["price"] - current_price)):
    print(f"  {c['type']} {c['price']} ({c['tf']})")

# ============================================================
# Load D1 data and run wick precision validation
# ============================================================

def load_json(path):
    with open(path) as f:
        return json.load(f)

# We need to save D1 data first - but let me just analyze from the bars we got
# D1 bars - save them
d1_bars_json = '''PLACEHOLDER_D1_BARS'''

# For now, let me do analysis with W1 data only
# Validate each candidate using W1 Wick Precision

def validate_level_w1(data, level, tolerances, is_res):
    """Wick precision validation on W1 data only"""
    results = []
    for tol in tolerances:
        interactions = 0
        wick_rejections = 0
        rejections = []
        
        for bar in data:
            touched = False
            if is_res:
                if bar["high"] >= level - tol and bar["high"] <= level + tol:
                    touched = True
                    body_top = max(bar["open"], bar["close"])
                    if bar["high"] > body_top:
                        wick_rejections += 1
                        bar_range = bar["high"] - bar["low"]
                        if bar_range > 0:
                            rejections.append((bar["high"] - body_top) / bar_range * 100)
            else:
                if bar["low"] >= level - tol and bar["low"] <= level + tol:
                    touched = True
                    body_bottom = min(bar["open"], bar["close"])
                    if bar["low"] < body_bottom:
                        wick_rejections += 1
                        bar_range = bar["high"] - bar["low"]
                        if bar_range > 0:
                            rejections.append((body_bottom - bar["low"]) / bar_range * 100)
            if touched:
                interactions += 1
        
        wp = (wick_rejections / interactions * 100) if interactions > 0 else 0
        avg_rej = sum(rejections) / len(rejections) if rejections else 0
        
        wp_score = min(wp, 100)
        intx_score = 100 if interactions >= 2 else (50 if interactions == 1 else 0)
        rej_score = min(avg_rej / 30 * 100, 100)
        tf_composite = wp_score * 0.50 + intx_score * 0.30 + rej_score * 0.20
        
        results.append({
            "tolerance": tol, "interactions": interactions,
            "wick_rejections": wick_rejections, "wick_precision": round(wp, 1),
            "avg_rejection_pct": round(avg_rej, 3), "tf_composite": round(tf_composite, 1),
        })
    
    best = max(results, key=lambda x: x["wick_precision"])
    return results, best

tolerances = [5, 10, 15, 20, 30, 50]

print(f"\n=== Level Validation (W1 only, current price: {current_price}) ===")
for c in sorted(unique, key=lambda x: abs(x["price"] - current_price)):
    is_res = c["type"] == "RES"
    _, best = validate_level_w1(W1_BARS, c["price"], tolerances, is_res)
    print(f"  {c['type']} {c['price']} | tol={best['tolerance']} | WP={best['wick_precision']}% | "
          f"intx={best['interactions']} | rej={best['avg_rejection_pct']:.1f}% | "
          f"score={best['tf_composite']:.1f} {'✅' if best['wick_precision'] >= 70 else '❌'}")

# Find best levels (WP >= 70% and interactions >= 2)
strong_levels = []
for c in sorted(unique, key=lambda x: abs(x["price"] - current_price)):
    is_res = c["type"] == "RES"
    _, best = validate_level_w1(W1_BARS, c["price"], tolerances, is_res)
    if best["wick_precision"] >= 70 and best["interactions"] >= 2:
        strong_levels.append({
            "price": c["price"], "type": c["type"],
            "wp": best["wick_precision"], "intx": best["interactions"],
            "rej": best["avg_rejection_pct"], "score": best["tf_composite"],
            "tol": best["tolerance"]
        })

print(f"\n=== STRONG Levels (WP >= 70%, intx >= 2) ===")
for l in strong_levels:
    print(f"  {l['type']} {l['price']} | WP={l['wp']}% | intx={l['intx']} | rej={l['rej']:.1f}% | "
          f"score={l['score']:.1f} (tol=±{l['tol']})")

# Output for plotting
print("\n=== PLOT OUTPUT ===")
for l in sorted(strong_levels, key=lambda x: abs(x["price"] - current_price)):
    print(f"PLOT|{l['type']}|{l['price']}|{l['score']:.0f}")
