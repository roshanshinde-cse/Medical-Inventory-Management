#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <tuple>
#include <cstdio>
#include <limits>

/*Changes to be Made:
1)GUI
2)
*/

/*=============================
 Abstract Base Class
=============================*/
class Record
{
public:
    virtual void display() const = 0;
    virtual void saveToFile(std::ofstream &out) const = 0;
    virtual ~Record() {}
};

// =============================
// Medicine Class
// =============================
class Medicine : public Record
{
private:
    std::string name;
    std::string batchNumber;
    std::string expiryDate;
    int quantity;
    float price;
    int originalQuantity;

public:
    Medicine() : quantity(0), price(0.0f), originalQuantity(0) {}

    Medicine(const std::string &n, const std::string &b, const std::string &e,
             int q, float p)
        : name(n), batchNumber(b), expiryDate(e), quantity(q), price(p), originalQuantity(q) {}

    std::string getName() const { return name; }
    std::string getBatchNumber() const { return batchNumber; }
    std::string getExpiryDate() const { return expiryDate; }
    int getQuantity() const { return quantity; }
    float getPrice() const { return price; }
    int getOriginalQuantity() const { return originalQuantity; }

    void setQuantity(int q) { quantity = q; }
    void setExpiryDate(const std::string &e) { expiryDate = e; }

    void display() const override
    {
        std::cout << std::left << std::setw(15) << name
                  << std::setw(12) << batchNumber
                  << std::setw(15) << expiryDate
                  << std::setw(8) << quantity
                  << std::setw(8) << price
                  << std::setw(10) << originalQuantity << "\n";
    }

    void saveToFile(std::ofstream &out) const override
    {
        out << name << "," << batchNumber << "," << expiryDate << ","
            << quantity << "," << price << "," << originalQuantity << "\n";
    }

    // Convert "YYYY-MM-DD" -> time_t. Returns -1 on parse error.
    time_t convertToTime(const std::string &dateStr) const
    {
        std::tm tm = {};
        if (sscanf(dateStr.c_str(), "%d-%d-%d", &tm.tm_year, &tm.tm_mon, &tm.tm_mday) != 3)
        {
            return (time_t)-1;
        }
        tm.tm_year -= 1900;
        tm.tm_mon -= 1;
        tm.tm_hour = 0;
        tm.tm_min = 0;
        tm.tm_sec = 0;
        return mktime(&tm);
    }

    // Check expiry
    bool isExpired() const
    {
        time_t exp = convertToTime(expiryDate);
        if (exp == (time_t)-1)
            return false; // treat invalid date as not expired
        time_t now = time(nullptr);
        return difftime(exp, now) < 0;
    }

    static Medicine loadFromFile(const std::string &line)
    {
        std::stringstream ss(line);
        std::string n, b, e, qStr, pStr, oqStr;
        getline(ss, n, ',');
        getline(ss, b, ',');
        getline(ss, e, ',');
        getline(ss, qStr, ',');
        getline(ss, pStr, ',');
        getline(ss, oqStr, ',');
        int q = 0;
        float p = 0.0f;
        try
        {
            if (!qStr.empty())
                q = std::stoi(qStr);
            if (!pStr.empty())
                p = std::stof(pStr);
        }
        catch (...)
        {
            q = 0;
            p = 0.0f;
        }
        int oq = oqStr.empty() ? q : std::stoi(oqStr);
        Medicine med(n, b, e, q, p);
        med.originalQuantity = oq;
        return med;
    }

    bool sell(int qty)
    {
        if (qty <= 0)
            return false;
        if (qty > quantity)
            return false;
        quantity -= qty;
        return true;
    }
};

// =============================
// InventoryManager
// =============================
class InventoryManager
{
private:
    std::vector<Medicine> inventory;
    const int LOW_STOCK_THRESHOLD = 10;

public:
    void loadFromFile(const std::string &filename)
    {
        inventory.clear();
        std::ifstream in(filename);
        std::string line;
        while (getline(in, line))
        {
            if (!line.empty())
            {
                Medicine med = Medicine::loadFromFile(line);
                inventory.push_back(med);
            }
        }
        in.close();
    }

    void saveToFile(const std::string &filename)
    {
        std::ofstream out(filename);
        for (const Medicine &med : inventory)
        {
            med.saveToFile(out);
        }
        out.close();
    }

    void addMedicine()
    {
        std::string name, batch, expiry;
        int quantity;
        float price;

        std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        std::cout << "Enter medicine name: ";
        getline(std::cin, name);
        std::cout << "Enter batch number: ";
        std::cin >> batch;
        std::cout << "Enter expiry date (YYYY-MM-DD): ";
        std::cin >> expiry;
        std::cout << "Enter original quantity: ";
        std::cin >> quantity;
        std::cout << "Enter price per unit: ";
        std::cin >> price;

        inventory.push_back(Medicine(name, batch, expiry, quantity, price));
        std::cout << "Medicine added successfully!\n";
    }

    void updateMedicine()
    {
        std::string batch;
        std::cout << "Enter batch number to update: ";
        std::cin >> batch;

        for (Medicine &med : inventory)
        {
            if (med.getBatchNumber() == batch)
            {
                int newQty;
                std::string newExp;
                std::cout << "Enter new quantity: ";
                std::cin >> newQty;
                std::cout << "Enter new expiry date (YYYY-MM-DD): ";
                std::cin >> newExp;
                med.setQuantity(newQty);
                med.setExpiryDate(newExp);
                std::cout << "Medicine updated successfully!\n";
                return;
            }
        }
        std::cout << "Medicine with batch number not found.\n";
    }

    void removeExpired()
    {
        auto it = inventory.begin();
        while (it != inventory.end())
        {
            if (it->isExpired())
            {
                std::cout << "Removing expired medicine: " << it->getName() << "\n";
                it = inventory.erase(it);
            }
            else
            {
                ++it;
            }
        }
        std::cout << "Expired medicines removed.\n";
    }

    void generateLowStockReport() const
    {
        std::cout << "\n=== LOW STOCK REPORT ===\n";
        for (const Medicine &med : inventory)
        {
            if (med.getQuantity() < LOW_STOCK_THRESHOLD)
            {
                med.display();
            }
        }
    }

    void generateExpiredReport() const
    {
        std::cout << "\n=== EXPIRED MEDICINES REPORT ===\n";
        for (const Medicine &med : inventory)
        {
            if (med.isExpired())
            {
                med.display();
            }
        }
    }

    void displayInventory() const
    {
        std::cout << "\n=== INVENTORY LIST ===\n";
        std::cout << std::left << std::setw(15) << "Name"
                  << std::setw(12) << "Batch"
                  << std::setw(15) << "Expiry"
                  << std::setw(8) << "Qty"
                  << std::setw(8) << "Price"
                  << std::setw(10) << "Original" << "\n";
        std::cout << "----------------------------------------------------------------\n";
        for (const Medicine &med : inventory)
        {
            med.display();
        }
    }

    // Multi-purchase billing system
    void buyMedicines()
    {
        std::vector<std::tuple<std::string, int, float>> billItems;
        char choice;
        float total = 0.0f;

        do
        {
            std::string batch;
            int qty;
            std::cout << "Enter batch number to purchase: ";
            std::cin >> batch;

            bool found = false;
            for (Medicine &med : inventory)
            {
                if (med.getBatchNumber() == batch)
                {
                    std::cout << "Enter quantity to buy: ";
                    std::cin >> qty;
                    if (med.sell(qty))
                    {
                        float cost = qty * med.getPrice();
                        total += cost;
                        billItems.push_back({med.getName(), qty, cost});
                        std::cout << "Added to bill: " << med.getName() << " x" << qty << "\n";
                    }
                    else
                    {
                        std::cout << "Not enough stock available.\n";
                    }
                    found = true;
                    break;
                }
            }
            if (!found)
                std::cout << "Medicine with batch number not found.\n";

            std::cout << "Do you want to buy another medicine? (y/n): ";
            std::cin >> choice;
        } while (choice == 'y' || choice == 'Y');

        if (!billItems.empty())
        {
            std::cout << "\n===== FINAL BILL =====\n";
            std::cout << std::left << std::setw(15) << "Medicine"
                      << std::setw(8) << "Qty"
                      << std::setw(10) << "Cost" << "\n";
            std::cout << "----------------------------------\n";
            for (auto &item : billItems)
            {
                std::cout << std::setw(15) << std::get<0>(item)
                          << std::setw(8) << std::get<1>(item)
                          << std::setw(10) << std::get<2>(item) << "\n";
            }
            std::cout << "----------------------------------\n";
            std::cout << "TOTAL: " << total << "\n";
            std::cout << "=======================\n";
        }
        else
        {
            std::cout << "No items purchased.\n";
        }
    }
};

// =============================
// Main
// =============================
int main()
{
    InventoryManager manager;
    manager.loadFromFile("inventory.txt");

    int choice;
    do
    {
        std::cout << "\n===== MEDICAL INVENTORY SYSTEM =====\n";
        std::cout << "1. Add New Medicine\n";
        std::cout << "2. Update Medicine\n";
        std::cout << "3. Remove Expired Medicines\n";
        std::cout << "4. Generate Low Stock Report\n";
        std::cout << "5. Generate Expired Report\n";
        std::cout << "6. Show Inventory\n";
        std::cout << "7. Buy Medicines (Generate Bill)\n";
        std::cout << "8. Save and Exit\n";
        std::cout << "Enter choice: ";
        std::cin >> choice;

        switch (choice)
        {
        case 1:
            manager.addMedicine();
            break;
        case 2:
            manager.updateMedicine();
            break;
        case 3:
            manager.removeExpired();
            break;
        case 4:
            manager.generateLowStockReport();
            break;
        case 5:
            manager.generateExpiredReport();
            break;
        case 6:
            manager.displayInventory();
            break;
        case 7:
            manager.buyMedicines();
            break;
        case 8:
            manager.saveToFile("inventory.txt");
            std::cout << "Inventory saved. Exiting...\n";
            break;
        default:
            std::cout << "Invalid choice.\n";
        }
    } while (choice != 8);

    return 0;
}
